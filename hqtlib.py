"""
Name:     hqtlib.py
Author:   Erik Anderson
Created:  April 25, 2019
Revised:  December 10, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better
          Spatial Analyst extension

This library contains modules required to run the Nevada Credit System, Colorado Habitat Exchange,
and Idaho Sage Steppe Mitigation Program HQTs.

Copyright 2017-2020 Environmental Incentives, LLC.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

# Import system modules
import arcpy
import os
import sys
import random
import numpy as np
from arcpy.sa import Con, IsNull
import util


# ----------------------------------------------------------------------------

# CUSTOM FUNCTIONS


def CheckToolVersion():
    """
    Adds warning if tool is being used past the specified date.
    Warning date is specified at the top of the ccslib script.
    :return: None
    """
    # ! Update warning date at top of script    
    from datetime import datetime
    today = datetime.today()
    warn_format = datetime.strptime(warn_date, "%m/%d/%Y")
    if today > warn_format:
        arcpy.AddWarning(
            """
            WARNING:: This version of the HQT Toolset is outdated.\n
            Please see the User's Guide for instructions on downloading
            the most recent version of the HQT Toolset.\n
            Results obtained from this tool are no longer valid.
            """
        )


def CheckOutSpatialAnalyst():
    """
    Attempts to check out spatial analyst extension. If unavailable, tool
    exits with error message.
    :return: None
    """
    # Check out Spatial Analyst extension
    try:
        arcpy.CheckOutExtension("Spatial")
        arcpy.AddMessage("Spatial Analyst extension checked out")
    except arcpy.ExecuteError:
        arcpy.AddError("Could not check out Spatial Analyst extension. "
                       "Please ensure Spatial Analyst extension is "
                       "available or contact your system administrator.")
        sys.exit(0)


def CheckPolygonInput(feature, required_fields=None, expected_fcs=None,
                      no_null_fields=None):
    """
    If the provided feature is not a polygon, is empty, does not contain
    the required fields, or has null values in the no null feilds, the tool
    exists with an error message. If the expected feature classes are not
    found in the gdb of the provided feature, the tool exists with an error
    message.
    :param feature: feature class
    :param required_fields: list of field names as strings
    :param expected_fcs: list of feature class names as strings
    :param no_null_fields: list of field names as strings
    :return: None
    """
    errorStatus = 0
    # Check feature type of provided feature class
    desc = arcpy.Describe(feature)
    if desc.shapeType != "Polygon":
        arcpy.AddError("ERROR:: Feature class provided is not a polygon.\n"
                       "Please provide a polygon feature.")
        errorStatus = 1

    # Check provided layer for features
    test = arcpy.GetCount_management(feature)
    count = int(test.getOutput(0))
    if count == 0:
        arcpy.AddError("ERROR:: Provide feature " + feature + " is empty. "
                       + feature + " must contain at least one feature.")
        errorStatus = 2

    # Check provided layer for required fields
    if required_fields:
        present_fields = [field.name for field in arcpy.ListFields(feature)]
        for field in required_fields:            
            if field not in present_fields:
                arcpy.AddError("ERROR:: Required field '" + field + "' is not "
                               "present in the provided feature: " + feature)
                errorStatus = 3

    # Check provided layer for attributes in required fields
    if not errorStatus == 3:
        if no_null_fields:
            for field in no_null_fields:
                with arcpy.da.SearchCursor(feature, field) as cursor:
                    for row in cursor:
                        if row[0] is None:
                            errorStatus = 4
                            arcpy.AddError("ERROR:: " + field + " field "
                                           "in feature " + feature
                                           + " contains Null values.")
                    
    # Check to ensure provided layer is in the project's geodatabase
    if expected_fcs:
        workspace_fcs = arcpy.ListFeatureClasses()
        for fc in expected_fcs:
            if fc not in workspace_fcs:
                wrong_workspace = arcpy.Describe(feature).path
                arcpy.AddError("ERROR:: Expected feature class " + fc
                               + " not found in workspace of provided feature "
                               + feature + ". Provided feature MUST be located "
                               + "in the project's unique geodatabase.")
                errorStatus = 5
                arcpy.AddError("Provided feature was found in workspace: "
                               + wrong_workspace)

    if errorStatus > 0:
        sys.exit(0)


def ProjectInput(input_feature, out_name, coordinate_system):
    """
    Projects the provided feature to the projection of the coordinate system.
    Honors feature selections.
    :param input_feature: a feature class, selected features will be honored
    :param out_name: a name to save the output as a string
    :param coordinate_system: the standard coordinate system as a
    SpatialReference object
    :return: the name of the projected feature as a string
    """
    # Project input feature to reference coordinate system
    selected_features = "in_memory/selected"
    arcpy.CopyFeatures_management(input_feature, selected_features)
    projected_feature = arcpy.Project_management(input_feature, out_name,
                                                 coordinate_system)

    # Clean up
    arcpy.Delete_management("in_memory")

    return projected_feature


def EliminateNonHabitat(Project_Area, out_name, habitat_bounds):
    """
    Clips the project area to the boundary of the habitat.
    :param Project_Area: a feature class representing the project area
    :param out_name: a name to save the output as a string
    :param habitat_bounds: a feature class representing the habitat
    boundaries
    :return: the name of the project area with non-habitat removed as
    a string
    """
    # Eliminate areas categorized as 'Non-Habitat' from the Project Area
    clip_features = habitat_bounds
    clipped_feature = arcpy.Clip_analysis(Project_Area, clip_features,
                                          out_name)

    return clipped_feature


def CreateIndirectImpactArea(in_data, parameter_values, out_name):
    """
    Buffers the provide feature class by the distance associated with the
    subytpe in the Parameter Values table. Provided feature class must have
    a field named 'Subtype' populated exactly the same as
    Anthro_Attribute_Table subtype codes.
    :param in_data: feature class with a field named 'Subtype' populated
    exactly the same as the Parameter Values table subtype codes.
    :param parameter_values: the Parameter Values table
    :param out_name: a name to save the output as a string
    :return: the name of the output as a string
    """
    # Join attribute table from AnthroAttributeTable.dbf based on Subtype
    # Get list of existing field names
    existingFields = arcpy.ListFields(in_data)
    fieldNames = [field.name.lower() for field in existingFields]
    # Perform join
    in_field = "Subtype"
    join_table = parameter_values
    join_field = "Subtype"
    fields = ["Distance", "Weight"]
    for field in fields:
        if field.lower() in fieldNames:
            arcpy.DeleteField_management(in_data, field)
            
    arcpy.JoinField_management(in_data, in_field, join_table, join_field,
                               fields)

    # Buffer Proposed_Surface_Disturbance based on Distance field
    in_features = in_data
    out_feature_class = out_name
    buffer_field = "Distance"
    line_side = "FULL"
    line_end_type = "ROUND"
    dissolve_option = "ALL"
    indirect_impact_area = arcpy.Buffer_analysis(in_features,
                                                 out_feature_class,
                                                 buffer_field, line_side,
                                                 line_end_type,
                                                 dissolve_option)

    # Merge all features with 0 distance (skipped by buffer)
    fc = arcpy.MakeFeatureLayer_management(in_data, "lyr")
    where_clause = """{} = {}""".format(
        arcpy.AddFieldDelimiters(fc, buffer_field), 0)
    arcpy.SelectLayerByAttribute_management(fc, "NEW_SELECTION",
                                            where_clause)
    
    merged_fc = arcpy.Merge_management([indirect_impact_area, fc], 
                                       'in_memory/merged')
    
    indirect_impact_area_merge = arcpy.Dissolve_management(
        merged_fc)

    return indirect_impact_area_merge


def CreateMapUnits(Project_Area, out_data):
    """
    Creates a copy of the project area feature class as the map units
    feature class
    :param Project_Area: a feature class, non-habitat must be removed
    :param out_data: a name to save the output as a string
    :return: the name of the output as a string
    """
    in_features = Project_Area
    out_feature_class = out_data
    map_units = arcpy.CopyFeatures_management(in_features, out_feature_class)

    return map_units


def CreateAnalysisArea(Project_Area, parameter_values, out_name):
    """
    Buffers the Project_Area layer by the maximum distance found in the
    Parameter Values table.
    :param Project_Area: the Project Area feature class, non-habitat must
    be removed
    :param parameter_values: the Parameter Values table
    :param out_name: a name to save the output as a string
    :return: the name of the output as a string
    """
    in_features = Project_Area
    out_feature_class = out_name
    line_side = "FULL"
    line_end_type = "ROUND"
    dissolve_option = "ALL"

    # identify maximum indirect effect distance for buffer
    effect_distances = [row[0] for row in arcpy.da.SearchCursor(
        parameter_values, "Distance") if isinstance(row[0], (int, float))]
    buffer_distance = max(effect_distances)

    Analysis_Area = arcpy.Buffer_analysis(in_features, out_feature_class,
                                          buffer_distance, line_side,
                                          line_end_type, dissolve_option)

    return Analysis_Area


def ClipAnthroFeatures(clip_features, anthro_feature_path):
    """
    Clips all provided anthropogenic feature layers to the Analysis Area
    boundary and saves to the project's gdb. Tool must be run while the
    project's gdb is the active workspace.
    :param clip_features: the Analysis Area feature class
    :param anthro_feature_path: the path to the Anthro_Features gdb
    :return: None
    """
    walk = arcpy.da.Walk(anthro_feature_path, datatype="FeatureClass",
                         type=["Polygon", "Polyline", "Point"])
    for dirpath, dirnames, filenames in walk:
        for filename in filenames:
            arcpy.AddMessage("Clipping " + filename)
            in_features = os.path.join(dirpath, filename)
            out_name = "Anthro_" + filename + "_Clip"
            arcpy.Clip_analysis(in_features, clip_features, out_name)


def BufferAnthroFeatures(filename, Parameter_Values):
    """
    Buffer line and point type anthropogenic features
    :param filename: the anthro feature to be buffered
    :param Parameter_Values: the Parameter Values table
    :return: None
    """
    # Join Buffer field from Parameter_Values table based on Subtype
    # Get list of existing field names
    existingFields = arcpy.ListFields(filename)
    fieldNames = [field.name.lower() for field in existingFields]
    # Perform join
    in_field = "Subtype"
    join_table = Parameter_Values
    join_field = "Subtype"
    fields = ["Buffer"]
    for field in fields:
        if field.lower() in fieldNames:
            arcpy.DeleteField_management(filename, field)
            
    arcpy.JoinField_management(filename, in_field, join_table, join_field,
                               fields)

    # Buffer Proposed_Surface_Disturbance based on Distance field
    in_features = filename
    out_feature_class = "AnthroP_" + filename[7:-5] + "_Clip"
    buffer_field = "Buffer"
    line_side = "FULL"
    line_end_type = "ROUND"
    dissolve_option = "NONE"
    arcpy.Buffer_analysis(in_features, out_feature_class, buffer_field,
                          line_side, line_end_type, dissolve_option)


def SelectPermanent(anthro_features, duration_field, temporary_codes,
                    reclass_code, reclass_subtype_field, out_name):
    """
    Creates the Permanent_Anthro_Features feature class
    :param anthro_features: the Projected_Anthro_Features feature class
    :param duration_field: the Surface_Disturbance field name
    :param temporary_codes: the codes used in the Surface_Disturbance
    field to signify temporary disturbance ("Term_Reclaimed, "Term_Retired"
    :param reclass_code: the code for reclassified surface disturance
    ("Term_Reclassified")
    :param reclass_subtype_field: The field name where reclassified subtypes
    are stored ("Reclassified_Subtype"
    :param out_name: a name to save the Permanent_Anthro_Features as a
    string.
    :return: None
    """
    # Select permanent features from proposed surface disturbance
    # by inverting selection of temporary features
    fc = arcpy.MakeFeatureLayer_management(anthro_features,
                                           "lyr")
    arcpy.SelectLayerByAttribute_management(fc, "CLEAR_SELECTION")

    for code in temporary_codes:
        where_clause = "{} = '{}'".format(
            arcpy.AddFieldDelimiters(fc, duration_field), code)
        arcpy.SelectLayerByAttribute_management(fc, "ADD_TO_SELECTION",
                                                where_clause)

    # Invert selection
    arcpy.SelectLayerByAttribute_management(fc, "SWITCH_SELECTION")

    # Save selected features
    permanent_features = arcpy.CopyFeatures_management(fc, out_name)

    # Remove selection and delete layer
    arcpy.SelectLayerByAttribute_management(fc, "CLEAR_SELECTION")
    arcpy.Delete_management("lyr")

    # Update subtype for features that will be reclassified post-project
    # Select features that will be reclassified post-project
    fc = arcpy.MakeFeatureLayer_management(permanent_features,
                                           "lyr")
    where_clause = "{} = '{}'".format(
        arcpy.AddFieldDelimiters(fc, duration_field), reclass_code)
    arcpy.SelectLayerByAttribute_management(fc, "NEW_SELECTION",
                                            where_clause)

    # Change subtype for reclassified features to reclassified
    # subtype
    with arcpy.da.UpdateCursor(fc, ["Subtype",
                                    reclass_subtype_field]) as cursor:
        for row in cursor:
            row[0] = row[1]
            cursor.updateRow(row)

    arcpy.Delete_management("lyr")

    return permanent_features


def AddIndirectBenefitArea(indirect_impact_area, mgmt_map_units):
    """
    Union the indirect impact/benefit area with the map units feature class
    and update attributes of the map units attribute table
    :param indirect_impact_area: feature class of indirect impacts or benefits
    :param mgmt_map_units: the Map Units feature class
    :return: the name of the unioned map units feature class as a string
    """
    # Combine the Map Units layer and Indirect Impact Layer
    # Remove from the Indirect_Impact_Area any existing Map_Units
    fileList = [indirect_impact_area, mgmt_map_units]
    out_name = "Map_Units_Indirect"
    Indirect_Map_Units, _ = util.RemoveFeatures(fileList, out_name)

    # Merge the created feature class with the Map Units feature class
    fileList = [mgmt_map_units, Indirect_Map_Units]
    out_name = "Map_Units_Union"
    map_units_union = util.MergeFeatures(fileList, out_name)

    # Update map unit IDs for indirect benefit area with next highest map
    # unit id
    feature = map_units_union
    current_muids = [row[0] for row in arcpy.da.SearchCursor(
        feature, "Map_Unit_ID") if isinstance(row[0], int)]
    # For credit projects that remove anthro features only, current_muids
    # will be empty, so use 1; else use max + 1.
    if not current_muids:
        next_muid = 1
    else:
        next_muid = max(current_muids) + 1
    
    with arcpy.da.UpdateCursor(feature, ["Indirect", "Map_Unit_ID",
                                         "Map_Unit_Name"]) as cursor: #KB deleted "Mesic" as column name
        for row in cursor:
            if row[0] == "True":
                row[1] = next_muid
                row[2] = "Indirect Benefits Area"
                cursor.updateRow(row)
            else:
                row[0] = "False"
                cursor.updateRow(row)

    # Rename Map_Units_Union to Map_Units
    map_units_out = util.RenameFeatureClass(map_units_union, mgmt_map_units)

    arcpy.Delete_management("Map_Units_Indirect")
    arcpy.Delete_management("Map_Units_Union")

    return map_units_out


def CreatePreDefinedMapUnits(Map_Units, in_features, field_name=None):
    """
    Intersects the Map Units feature class with the in_features feature class.
    A field name may be provided from the in_features to include in the output
    feature class as a label for the map unit, the field will be updated with
    'N/A' for any map units that don't interstect the in_features.
    :param Map_Units: the Map Units feature class
    :param in_features: a feature class to create pre-defined map units from
    :param field_name: the name of a field in the in_features attribute table
    to preserve in the output. Will be updated with 'N/A' if no overlap.
    :return: None
    """
    # Clip the provided features to the Map_Units layer
    clip_features = Map_Units
    out_feature_class = "in_memory/clip"
    arcpy.Clip_analysis(in_features, clip_features, out_feature_class)

    # Union the clipped features and the Map Units layer
    FCs = [Map_Units, out_feature_class]
    out_feature_class = "in_memory/Map_Units_Union"
    Map_Units_Union = arcpy.Union_analysis(FCs, out_feature_class)

    # Overwrite the existing Map_Units layer
    util.RenameFeatureClass(Map_Units_Union, Map_Units)

    # Populate blank fields with N/A
    if field_name:
        with arcpy.da.UpdateCursor(Map_Units, field_name) as cursor:
            for row in cursor:
                if row[0] is None or row[0] == "":
                    row[0] = "N/A"
                    cursor.updateRow(row)

    # # Add fields and populate with 'True' wherever a new map unit was created
    # if field_name:
    #     fieldsToAdd = [field_name]
    #     fieldTypes = ["TEXT"]
    #     AddFields(Map_Units, fieldsToAdd, fieldTypes)
    #     FID_field = "FID_clip"
    #     with arcpy.da.UpdateCursor(Map_Units,
    #                                [FID_field, field_name]) as cursor:
    #         for row in cursor:
    #             if row[0] > -1:
    #                 row[1] = "True"
    #             else:
    #                 row[1] = "N/A"
    #             cursor.updateRow(row)

    # Clean up
    arcpy.Delete_management("in_memory")


def DissolveMapUnits(Map_Units, allowable_fields, out_name, anthro_features):
    """
    Dissolves the Map Units feature class with the fields provided in the
    allowable fields. Deletes any anthropogenic features provided.
    :param Map_Units: the Map Units feature class
    :param allowable_fields: a list of field names as strings
    :param out_name: a name to save the output as a string
    :param anthro_features: anthropogenic features to delete from the
    Map Units feature class, usually Current_Anthro_Features
    :return: the name of the output as a string
    """
    if anthro_features:
        # Clip and union Current Anthro Features within Map Units layer to identify
        # map units that correspond with current surface disturbance
        in_features = anthro_features
        clip_features = Map_Units
        out_feature_class = "in_memory/Anthro_Features_ClippedToProject"
        anthroClipped = arcpy.Clip_analysis(in_features, clip_features,
                                            out_feature_class)

        in_features = [anthroClipped, Map_Units]
        out_feature_class = "in_memory/Map_Units_SurfaceDisturbance"
        MUSurfaceDisturbance = arcpy.Union_analysis(in_features,
                                                    out_feature_class)

        # Populate Map Unit ID, MapUnitName, and Meadow attributes for all map
        # units that correspond with surface disturbance
        feature = arcpy.MakeFeatureLayer_management(MUSurfaceDisturbance, "lyr")
        arcpy.SelectLayerByLocation_management(feature, "WITHIN", anthroClipped)
        arcpy.DeleteFeatures_management(feature)

        # Clear selection
        arcpy.SelectLayerByAttribute_management(feature, "CLEAR_SELECTION")
        arcpy.Delete_management("lyr")

        in_features = MUSurfaceDisturbance

    else:
        in_features = Map_Units

    # Dissolve map units layer and simplify attribute table fields
    out_feature_class = out_name
    dissolve_fields = []
    for field in arcpy.ListFields(Map_Units):
        if field.name in allowable_fields:
            dissolve_fields.append(field.name)
    map_units_dissolve = arcpy.Dissolve_management(
        in_features, out_feature_class, dissolve_fields
        )

    # Combine notes fields
    # Retrieve lists of map unit ids and notes
    fc = Map_Units
    id_field = arcpy.ListFields(fc, "*_Unit_ID")[0].name
    fields = [id_field, "Notes"]
    mu_ids = []
    mu_notes = []
    with arcpy.da.SearchCursor(fc, fields) as cursor:
        for row in cursor:
            mu_ids.append(row[0])
            mu_notes.append(row[1])

    # Add notes field back to map units dissolve
    util.AddFields(map_units_dissolve, ["Notes"], ["TEXT"])

    # Update map unit dissolve table
    fc = map_units_dissolve
    fields = [id_field, "Notes"]
    seperator = "; "
    with arcpy.da.UpdateCursor(fc, fields) as cursor:
        for row in cursor:
            try:
                # Get unique list of notes from map units dissolve
                new_notes = []
                for note, mu_id in zip(mu_notes, mu_ids):
                    if mu_id == row[0]:
                        new_notes.append(note)
                new_notes_unique = list(set(new_notes))
                new_notes_unique = [note for note in new_notes_unique \
                                    if note is not None]
                new_notes_string = seperator.join(new_notes_unique)
                # Truncate long notes (should be 255 chararcters)
                field_length = arcpy.ListFields(fc, fields[1])[0].length
                if len(new_notes_string) > field_length:
                    new_notes_string = new_notes_string[:field_length]
                # Update table
                row[1] = new_notes_string
                cursor.updateRow(row)
            except:
                arcpy.AddMessage("Notes field not populated, refer to original "
                                 "Map_Units feature class for notes")

    # Clean up
    arcpy.Delete_management("in_memory")

    return map_units_dissolve


def CalcAcres(feature):
    """
    Adds field 'Acres' to provided feature and calculates area in acres.
    Feature may not have field Acres in table.
    :param feature: feature class to calculate area of features
    :return: None
    """
    inTable = feature
    fieldName = "Acres"
    fieldType = "DOUBLE"
    expression = "!shape.area@ACRES!"    
    arcpy.AddField_management(inTable, fieldName, fieldType)
    arcpy.CalculateField_management(inTable, fieldName, expression,
                                    "PYTHON_9.3", "")


def CalcProportion(Map_Units_Dissolve, in_feature, out_feature_class,
                   field_name):
    """
    Calculates the proportion of each map unit in each category.
    :param Map_Units_Dissolve: the Map Units Dissolve feature class
    :param in_feature: the feature class to calculate proportions of
    :param out_feature_class: a name to save the output as a string
    :param field_name: the name of a field to add where the proportion
    will be saved as a string
    :return: None
    """
    # Interesct map unit layer and provided feature
    in_features = [Map_Units_Dissolve, in_feature]
    out_feature_class = out_feature_class
    arcpy.Intersect_analysis(in_features, out_feature_class)

    # Calculate area of each split map unit
    inTable = out_feature_class
    fieldName = "Temp_Acres"
    fieldType = "DOUBLE"
    expression = "!shape.area@ACRES!"    
    arcpy.AddField_management(inTable, fieldName, fieldType)
    arcpy.CalculateField_management(inTable, fieldName, expression,
                                    "PYTHON_9.3", "")

    # Calculate proportion of map unit per category
    arcpy.AddField_management(out_feature_class, field_name, "DOUBLE")
    with arcpy.da.UpdateCursor(out_feature_class,
                               [field_name, "Temp_Acres", "Acres"]) as cursor:
        for row in cursor:
            row[0] = row[1]/row[2]
            cursor.updateRow(row)


def CalcZonalStats(in_zone_data, zone_field, in_value_raster, out_table):
    """
    Resamples inValueRaster to 5m pixel size and calculates the average value
    within each map unit. Higher resolution required for map units <5 acres.
    :param in_zone_data: the Map Units Dissolve feature class
    :param zone_field: the field to use as zone field, must be integer and
    cannot be OBJECTID
    :param in_value_raster: raster dataset or basename as a string
    :param out_table: a name to save the ouput table as a string
    :return: None
    """
    # Convert null values to 0 so that they are not ignored when summarizing
    in_value_raster = Con(IsNull(in_value_raster),0,in_value_raster)

    # Resample to avoid small map units returning null values
    resample = True
    if resample:
        # Resample raster
        tmp_raster = "sub_raster"
        arcpy.Resample_management(in_value_raster, tmp_raster, "5", "NEAREST")
    else:
        tmp_raster = in_value_raster
    # Calculate zonal statistics
    arcpy.gp.ZonalStatisticsAsTable_sa(in_zone_data, zone_field, tmp_raster,
                                    out_table, "DATA", "MEAN")
    if resample:
        arcpy.Delete_management(tmp_raster)


def JoinMeanToTable(in_data, zonal_stats, zone_field, field_name):
    """
    Joins the MEAN field of the provided table to the Map_Units_Dissolve
    attribute table, deleting existing versions of the field if neccesary.
    :param in_data: the Map Unit Dissolve feature class
    :param zonal_stats: the table with statistics to join
    :param zone_field: the name of the field to join to ("Map_Unit_ID")
    :param field_name: a field name to save the joined field as a string
    :return: None
    """
    # Delete existing instances of the new field or MEAN, if present
    existingFields = arcpy.ListFields(in_data)
    for field in existingFields:
        if field.name.lower() == field_name.lower():
            arcpy.DeleteField_management(in_data, field.name)
        if field.name == "MEAN":
            arcpy.DeleteField_management(in_data, field.name)

    # Join MEAN field from ZonalStats table to Map_Units_Dissolve
    joinTable = zonal_stats
    joinField = zone_field
    field = "MEAN"
    arcpy.JoinField_management(in_data, zone_field, joinTable, joinField,
                               field)

    # Change name of joined field
    arcpy.AlterField_management(in_data, field, field_name)


def GenerateTransects(workspace, Map_Units, field_name, out_name):
    """
    Creates random transect locations
    :param workspace: the project's unique geodatabase
    :param Map_Units: the Map_Units_Dissolve feature class with number of
    transects identified in the attribute table
    :param field_name: the field in the attribute table with transect
    requirements defined
    :param out_name: a name to save the output as
    :return: the name of the output as a string
    """
    arcpy.AddMessage("Generating random transect locations within each map "
                     "unit")
    # Create random points in buffered map units
    transects = arcpy.CreateRandomPoints_management(workspace, out_name,
                                                    Map_Units,
                                                    "#", field_name, 25)
    return transects


def AddTransectFields(Transects):
    """
    Inputs: a point shapefile or feature class containing transect points.
    Adds fields for Bearings and UTM Easting and Northing to the provided
    feature.
    Returns: none
    """
    # Add fields for Bearing
    arcpy.AddMessage("Generate random bearing directions for each transect")
    fieldsToAdd = ["Bearing1", "Bearing2", "Bearing3"]
    fieldTypes = ["SHORT", "SHORT", "SHORT"]
    util.AddFields(Transects, fieldsToAdd, fieldTypes)
    with arcpy.da.UpdateCursor(Transects, fieldsToAdd) as cursor:
        for row in cursor:
            row[0] = random.randint(0, 360)
            row[1] = random.randint(0, 360)
            row[2] = random.randint(0, 360)
            cursor.updateRow(row)
            
    # Add fields for UTM
    arcpy.AddMessage("Calculate the UTM Easting and Northing for each transect")
    fieldsToAdd = ["UTM_E", "UTM_N"]
    fieldTypes = ["DOUBLE", "DOUBLE"]
    util.AddFields(Transects, fieldsToAdd, fieldTypes)
    arcpy.AddGeometryAttributes_management(Transects, "POINT_X_Y_Z_M")
    with arcpy.da.UpdateCursor(
            Transects, ["UTM_E", "UTM_N", "POINT_X", "POINT_Y"]) as cursor:
        for row in cursor:
            row[0] = row[2]
            row[1] = row[3]
            cursor.updateRow(row)
    arcpy.DeleteField_management(Transects, "POINT_X")
    arcpy.DeleteField_management(Transects, "POINT_Y")


def TransectJoin(Map_Units_Dissolve, Transects, out_name):
    """
    Creates a spatial join of the Transects feature class with the Map Units
    Dissolve feature class
    :param Map_Units_Dissolve: Map Units Dissolve feature class
    :param Transects: Transects feature class
    :param out_name: a name to save the output as a string
    :return: None
    """
    arcpy.AddMessage("Executing spatial join of Transects and "
                     "Map_Unit_Dissolve layer")
    # Execute join
    arcpy.SpatialJoin_analysis(Transects, Map_Units_Dissolve,
                               out_name, "JOIN_ONE_TO_MANY",
                               "KEEP_ALL", "#", "WITHIN")


def ExportToExcel(input_table, Project_Folder, Project_Name):
    """
    Exports the attribute table of the provided feature or table as a .xls
    file and saves to the project folder with the project name appended.
    :param input_table: a table to be exported
    :param Project_Folder: the directory of the project's unique folder
    :param Project_Name: the unique name of the project as a string
    :return: None
    """
    # Update message
    arcpy.AddMessage("Exporting " + str(input_table)
                     + " attribute tables to "
                     "Excel within the Project Folder")
    # Export tables
    output_file = os.path.join(Project_Folder, str(Project_Name) + "_"
                               + str(input_table) + ".xls")
    arcpy.TableToExcel_conversion(input_table, output_file)
