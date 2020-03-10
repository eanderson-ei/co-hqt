"""
Name:     util.py
Author:   Erik Anderson
Created:  December 10, 2019
Revised:  December 10, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better
          Spatial Analyst extension

This library contains utility functions required to run the Nevada Credit 
System, Colorado Habitat Exchange, and Idaho Sage Steppe Mitigation Program 
HQTs.

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
import numpy as np


# ----------------------------------------------------------------------------

# UTILITY FUNCTIONS

def Str2Bool(string):
    """
    Converts a string to Python boolean. If not 'true' in lowercase, returns
    False.
    :param string: a string of True or False, not cap sensitive
    :return: Boolean
    """
    if string == 'True' or string == 'true':
        return True
    else:
        return False


def AddAnthroToMap(workspace, anthro_feature):
    """
    Adds anthropogenic features to the map document by replacing the existing
    state-wide layer with the clipped (project-specific) feature (replacing
    existing maintains the subtype templates for editing). Note that clipped
    anthro features must have 'Anthro_' and '_clip' (not cap sensitive) as
    prefix and suffix.
    :param workspace: the gdb with the clipped (project-specific) anthro features
    :param anthro_feature: the anthro feature to be added to the map document
    :return: None
    """

    if arcpy.ListInstallations()[0] == 'arcgispro':#switch for arcpro and gis desktop
        p = arcpy.mp.ArcGISProject("CURRENT")
        m = p.activeMap
        try:
            for existingLayer in m.listLayers():
                if existingLayer.name == anthro_feature[7:-5]:
                    #workspace_type = "FILEGDB_WORKSPACE"
                    #dataset_name = anthro_feature
                    new_conn_prop = existingLayer.connectionProperties
                    new_conn_prop['connection_info']['database'] = workspace
                    new_conn_prop['dataset'] = anthro_feature
                    #existingLayer.replaceDataSource(workspace, workspace_type,
                                                   # dataset_name)
                    existingLayer.updateConnectionProperties(existingLayer.connectionProperties,new_conn_prop)
            #arcpy.RefreshActiveView()
        except arcpy.ExecuteError:
            for existingLayer in m.listLayers():
                if existingLayer.name == anthro_feature:
                    arcpy.mp.RemoveLayer(existingLayer)
            refLayer = m.ListLayers("Analysis_Area")[0]
            m.insertLayer(m, refLayer, anthro_feature, "AFTER")
        del p, m
    else: 
    # Add layer to map
        arcpy.AddMessage("Adding layer to map document")
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame
        layer = arcpy.mapping.Layer(anthro_feature)
        try:
            for existingLayer in arcpy.mapping.ListLayers(mxd, "", df):
                if existingLayer.name == layer.name[7:-5]:
                    workspace_type = "FILEGDB_WORKSPACE"
                    dataset_name = anthro_feature
                    existingLayer.replaceDataSource(workspace, workspace_type,
                                                    dataset_name)
            arcpy.RefreshActiveView()
        except arcpy.ExecuteError:
            for existingLayer in arcpy.mapping.ListLayers(mxd, "", df):
                if existingLayer.name == layer.name:
                    arcpy.mapping.RemoveLayer(df, existingLayer)
            refLayer = arcpy.mapping.ListLayers(mxd, "Analysis_Area", df)[0]
            arcpy.mapping.InsertLayer(df, refLayer, layer, "AFTER")
        del mxd, df, layer


def AddCodedTextDomain(feature_list, workspace, domain_name, code_list,
                       assign_default=False, populate_default=False):
    """
    Applies the code_list as a domain to the list of feature classes.
    Domain must be the same as the field name to which it is being applied.
    :param feature_list: list of feature classes
    :param workspace: the project's unique gdb
    :param domain_name: name of the domain as a string, must be same as name
    of field to which it is applied
    :param code_list: list of codes as strings
    :param assign_default: True to assign the first code in the code_list as
    default
    :param populate_default: True to populate existing features with the
    default code
    :return: None
    """
    # Create unique list from provided
    uniqueCodes = []
    for code in code_list:
        if code not in uniqueCodes:
            uniqueCodes.append(code)
    # Check for existence of domain; update domain if present, add domain if not
    desc = arcpy.Describe(workspace)
    domains = desc.domains
    if domain_name in domains:
        arcpy.AddMessage(domain_name + " is already specified as a domain")
        try:
            # try removing from all fields in all feature classes
            existingFeatures = arcpy.ListFeatureClasses()
            for existingFeature in existingFeatures:
                fields = arcpy.ListFields(existingFeature)
                for field in fields:
                    if field.domain == domain_name:
                        arcpy.RemoveDomainFromField_management(existingFeature,
                                                                field.name)
                        arcpy.AddMessage(domain_name + " domain removed from "
                                        + existingFeature + " " + field.name
                                        + " field")
                # try removing from all fields in all subtypes
                # Credit to:(https://community.esri.com/thread/
                # 198384-how-to-remove-domain-from-field-for-gdb)
                subtypes = arcpy.da.ListSubtypes(existingFeature)
                for stcode, stdict in list(subtypes.items()):
                    for stkey in list(stdict.keys()):
                        # if there is a Subtype Field
                        if not stdict['SubtypeField'] == '':
                            st_code = "'{}: {}'".format(stcode, stdict['Name'])
                        # if no Subtype Field, use "#" in RemoveDomainFromField
                        # for subtype_code
                        else:
                            st_code = "#"
                        if stkey == 'FieldValues':
                            fields = stdict[stkey]
                            for field, fieldvals in list(fields.items()):
                                # if field has a domain
                                if not fieldvals[1] is None:
                                    # and the domain is in our list
                                    if fieldvals[1].name == domain_name:
                                        # remove the domain
                                        arcpy.AddMessage(fieldvals[1].name
                                                            + " domain removed "
                                                            + "from " + existingFeature
                                                            + " field: " + field
                                                            + " subtype: " + st_code)
                                        arcpy.RemoveDomainFromField_management(
                                            existingFeature, field, st_code)

            arcpy.DeleteDomain_management(workspace, domain_name)
            arcpy.CreateDomain_management(workspace, domain_name,
                                            "Valid " + domain_name + "s",
                                            "TEXT", "CODED")

            for code in uniqueCodes:
                arcpy.AddCodedValueToDomain_management(workspace, domain_name,
                                                        code, code)
            for feature in feature_list:
                try: 
                    arcpy.AssignDomainToField_management(feature, domain_name,
                                                        domain_name)
                    # Check to make sure subtypes exist
                    subtypes = arcpy.da.ListSubtypes(feature)
                    if len(subtypes) == 1 and subtypes[0]['SubtypeField'] == '':
                        pass
                    else:
                        st_codes = [str(stcode) for stcode, stdict in list(subtypes.items())]
                        arcpy.AssignDomainToField_management(feature, domain_name,
                                                            domain_name, st_codes)

                except arcpy.ExecuteError:
                    arcpy.AddMessage("--------------------------------"
                                     "\n" + domain_name
                                     + " domain for feature \n\n"
                                     + str(feature) + "\n\n"
                                     + "could not be updated. Use "
                                     "caution when populating attribute\n"
                                     "---------------------------------")
            arcpy.AddMessage(domain_name + " domain updated")

        except arcpy.ExecuteError:
            arcpy.AddMessage(domain_name + " domain could not be updated. Use "
                             "caution when populating attribute")
    else:
        arcpy.CreateDomain_management(workspace, domain_name,
                                      "Valid " + domain_name + "s",
                                      "TEXT", "CODED")
        for code in uniqueCodes:
            arcpy.AddCodedValueToDomain_management(workspace, domain_name,
                                                   code, code)
        for feature in feature_list:
            try: 
                arcpy.AssignDomainToField_management(feature, domain_name,
                                                     domain_name)
                # Check to make sure subtypes exist
                subtypes = arcpy.da.ListSubtypes(feature)
                if len(subtypes) == 1 and subtypes[0]['SubtypeField'] == '':
                    pass
                else:
                    st_codes = [str(stcode) for stcode, stdict in list(subtypes.items())]
                    arcpy.AssignDomainToField_management(feature, domain_name,
                                                        domain_name, st_codes)                

            except arcpy.ExecuteError:
                arcpy.AddMessage(domain_name + " domain could not be updated. Use "
                                 "caution when populating attribute")
            
        arcpy.AddMessage(domain_name + " domain updated")
        
    # Assign the first value as the default
    if assign_default:
        for feature in feature_list:
            subtypes = arcpy.da.ListSubtypes(feature)
            if len(subtypes) == 1 and subtypes[0]['SubtypeField'] == '':
                arcpy.AssignDefaultToField_management(feature, domain_name, 
                                                      uniqueCodes[0])
            else:
                st_codes = [str(stcode) for stcode, stdict in list(subtypes.items())]
                arcpy.AssignDefaultToField_management(feature, domain_name, 
                                                    uniqueCodes[0], st_codes)

    # Populate field with default values if Null
    if populate_default:
        arcpy.AddMessage("Populating default values")
        for feature in feature_list:
            where_clause = "{0} = '' OR {0} IS NULL".format(
                arcpy.AddFieldDelimiters(feature, domain_name)
                )
            with arcpy.da.UpdateCursor(feature, domain_name, where_clause) as cursor:
                for row in cursor:
                    row[0] = uniqueCodes[0]
                    cursor.updateRow(row)


def AddToMap(feature_or_raster, layer_file=None, zoom_to=False):
    """
    Adds provided to the map document after removing any layers of the same
    name.
    :param feature_or_raster: feature class or raster dataset
    :param layer_file: layer file
    :param zoom_to: True to zoom to the added object
    :return: None
    """
    # Add layer to map
    arcpy.AddMessage("Adding layer to map document")
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        m= p.activeMap
        layer_path = arcpy.Describe(feature_or_raster).catalogPath #arcpy.Describe calls metadata, so this gives full path
        for existingLayer in m.listLayers(m):
            if existingLayer.name == feature_or_raster:
               m.remove_layer(existingLayer)
        m.addDataFromPath(layer_path)
        # TODO: revisit layer file application in Pro.
        if layer_file:
            arcpy.ApplySymbologyFromLayer_management(feature_or_raster, layer_file)
        #if zoom_to:
         #   m.extent = layer.getSelectedExtent()
        del p, m

    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame
        layer_path = arcpy.Describe(feature_or_raster).catalogPath
        layer = arcpy.mapping.Layer(layer_path)
        for existingLayer in arcpy.mapping.ListLayers(mxd, "", df):
            if existingLayer.name == layer.name:
                arcpy.mapping.RemoveLayer(df, existingLayer)
        arcpy.mapping.AddLayer(df, layer)
        if layer_file:
            arcpy.ApplySymbologyFromLayer_management(layer.name, layer_file)
        if zoom_to:
            df.extent = layer.getSelectedExtent()
        del mxd, df, layer


def AddFields(input_feature, field_to_add, field_types, copy_existing=False):
    """
    Adds provided fields to the input_feature, removes or copies existing of
    the same name.
    :param input_feature: a feature class
    :param field_to_add: a list of field names as strings
    :param field_types: a list of field types as strings, in order of fields_
    to_add
    :param copy_existing: True to create a copy of any existing field with
    same name as field to add
    :return: None
    """
    # Create dictionary of field types mapped to fields to add
    fieldTypesDict = dict(list(zip(field_to_add, field_types)))

    # Copy fields if they exist and delete original
    existingFields = arcpy.ListFields(input_feature)
    fieldNames = [each.name.lower() for each in existingFields]
    for field in field_to_add:
        if field.lower() in fieldNames:
            arcpy.AddMessage(field + " field exists.")
            if copy_existing:
                arcpy.AddMessage("Copying to new field named " + field
                                 + "_copy.")
                fieldIndex = fieldNames.index(field.lower())
                if field.lower() + "_copy" in fieldNames:
                    arcpy.AddMessage("Deleting field " + field + "_copy")
                    arcpy.DeleteField_management(input_feature,
                                                 field + "_copy")
                arcpy.AddField_management(input_feature, field + "_copy",
                                          existingFields[fieldIndex].type)
                with arcpy.da.UpdateCursor(
                        input_feature, [field, field + "_copy"]) as cursor:
                    try:
                        for row in cursor:
                            row[1] = row[0]
                            cursor.updateRow(row)
                    except arcpy.ExecuteError:
                        arcpy.AddMessage("Unable to copy from " + field
                                         + " to " + field + "_copy.")
            arcpy.AddMessage("Deleting original field.")
            arcpy.DeleteField_management(input_feature, field)

    # Add fields
    for field in field_to_add:
        # arcpy.AddMessage("Adding " + field + " field")
        arcpy.AddField_management(input_feature, field,
                                  fieldTypesDict[field],
                                  field_length=50)


def AddRangeDomain(feature, workspace, domain_name, range_low, range_high):
    """
    Applies the range domain to the feature. Removes domain from any existing
    features if necessary.
    :param feature: a feature class
    :param workspace: the project's unique gdb
    :param domain_name: the name of the domain as a string
    :param range_low: integer or float
    :param range_high: integer or float
    :return: None
    """
    # Check for existence of domain; update domain if present, add domain if
    # not
    desc = arcpy.Describe(workspace)
    domains = desc.domains

    if domain_name in domains:
        arcpy.AddMessage(domain_name + " is already specified as a domain")
        try:
            # try removing from all fields in all feature classes
            existingFeatures = arcpy.ListFeatureClasses()
            for existingFeature in existingFeatures:
                fields = arcpy.ListFields(existingFeature)
                for field in fields:
                    if field.domain == domain_name:
                        table = os.path.join(workspace, existingFeature)
                        arcpy.RemoveDomainFromField_management(table,
                                                               field.name)
                        arcpy.AddMessage(domain_name + " domain removed from "
                                         + existingFeature + " " + field.name
                                         + " field")
                # try removing from all fields in all subtypes
                subtypes = arcpy.da.ListSubtypes(existingFeature)
                for stcode, stdict in list(subtypes.items()):
                    for stkey in list(stdict.keys()):
                        # if there is a Subtype Field
                        if not stdict['SubtypeField'] == '':
                            st_code = "'{}: {}'".format(stcode, stdict['Name'])
                        # if no Subtype Field, use "#" in RemoveDomainFromField
                        # for subtype_code
                        else:
                            st_code = "#"
                        if stkey == 'FieldValues':
                            fields = stdict[stkey]
                            for field, fieldvals in list(fields.items()):
                                # if field has a domain
                                if not fieldvals[1] is None:
                                    # and the domain is in our list
                                    if fieldvals[1].name == domain_name:
                                        # remove the domain
                                        arcpy.AddMessage(fieldvals[1].name
                                                         + " domain removed "
                                                         + "from " + existingFeature
                                                         + " field: " + field
                                                         + " subtype: " + st_code)
                                        arcpy.RemoveDomainFromField_management(
                                            existingFeature, field, st_code
                                            )
            arcpy.DeleteDomain_management(workspace, domain_name)
            arcpy.CreateDomain_management(workspace, domain_name, domain_name
                                          + " must be integer", "SHORT", "RANGE")
            arcpy.SetValueForRangeDomain_management(workspace, domain_name,
                                                    range_low, range_high)
            arcpy.AssignDomainToField_management(feature, domain_name,
                                                 domain_name)
            arcpy.AddMessage(domain_name + " domain updated")
        except arcpy.ExecuteError:
            arcpy.AddMessage(domain_name + " domain could not be updated")
    else:
        arcpy.CreateDomain_management(workspace, domain_name, domain_name
                                      + " must be integer", "SHORT", "RANGE")
        arcpy.SetValueForRangeDomain_management(workspace, domain_name,
                                                range_low, range_high)
        arcpy.AssignDomainToField_management(feature, domain_name, domain_name)
        arcpy.AddMessage(domain_name + " domain updated")


def AddSubtypeDomains(feature_list, workspace, Parameter_Values):
    """
    Applies the subtypes listed in the Anthro_Attribute_Table as a domain
    to the Subtype field in the anthro feature classes.
    :param feature_list: a list of anthro features
    :param workspace: the project's unique gdb
    :param Parameter_Values: the Parameter_Values table
    :return: None
    """
    arcpy.TableToDomain_management(Parameter_Values,
                                   "Subtype", "Subtype", workspace,
                                   "Subtype", "Valid anthropogenic subtypes",
                                   "REPLACE")
    for feature in feature_list:
        arcpy.AssignDomainToField_management(feature, "Subtype", "Subtype")


def AdoptParameter(provided_input, parameter_name, preserve_existing=True):
    """
    Copies the provided input into the geodatabase as the parameter_name
    parameter. If a feature class already exists with the parameter_name,
    a unique copy will be saved (with preserve_existing=True).
    Workspace must be defined as project's unique geodatabase before
    calling this function.
    :param provided_input: a feature class or shapefile
    :param parameter_name: the name to save the provided_input as string
    :param preserve_existing: True to avoid overwriting
    :return: the name of the adopted parameter as a string
    """
    # Save a copy of the existing feature class if it already exists
    if preserve_existing:
        if arcpy.Exists(parameter_name):
            new_parameter_name = arcpy.CreateUniqueName(parameter_name)
            arcpy.CopyFeatures_management(parameter_name, new_parameter_name)

    # Copy providedInput to temporary memory to allow overwriting
    arcpy.CopyFeatures_management(provided_input, "in_memory/tmp_provided")

    # Delete existing layers in the TOC of the paramaterName
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        m = p.activeMap
        for _ in m.listLayers():
            arcpy.Delete_management(parameter_name)
    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        for _ in arcpy.mapping.ListLayers(mxd, parameter_name):
            arcpy.Delete_management(parameter_name)

    # Delete feature classes in the geodatabase
    for _ in arcpy.ListFeatureClasses(parameter_name):
        arcpy.Delete_management(parameter_name)

    # Execute renaming
    adopted_parameter = arcpy.CopyFeatures_management(
        "in_memory/tmp_provided", parameter_name
        )

    # Clean up
    arcpy.Delete_management("in_memory")

    return adopted_parameter


def ClearSelectedFeatures(fc):
    """
    Removes a selection from the provided feature class
    :param fc: a feature class
    :return: None
    """
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        m = p.activeMap
        for lyr in m.listLayers(fc):
            if lyr.getSelectionSet():
                arcpy.AddMessage("clearing {} selected features for "
                                 "layer: '{}'".format(len(lyr.getSelectionSet()),
                                                      lyr.name))
                arcpy.management.SelectLayerByAttribute(lyr, 'CLEAR_SELECTION')
        del m
    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        for lyr in arcpy.mapping.ListLayers(mxd, fc):
            if lyr.getSelectionSet():
                arcpy.AddMessage("clearing {} selected features for "
                                 "layer: '{}'".format(len(lyr.getSelectionSet()),
                                                      lyr.name))
                arcpy.management.SelectLayerByAttribute(lyr, 'CLEAR_SELECTION')
        del mxd


def CreateTemplate(workspace, out_name, coordinate_system):
    """
    Creates a template to digitize proposed surface disturbance  or credit
    project boundary in the workspace provided.
    :param workspace: the project's unique gdb
    :param out_name: a name for the template as a string
    :param coordinate_system: the standard coordinate system as a
    SpatialReference object
    :return: None
    """
    # Create an empty feature class
    template_features = arcpy.CreateFeatureclass_management(
        workspace, out_name, "POLYGON", spatial_reference=coordinate_system
        )

    return template_features


def MergeFeatures(file_list, out_name):
    """
    Merges all feature classes into a single feature class.
    :param file_list: a list of feature classes to be merged
    :param out_name: the name to save the output as a string
    :return: the merged features
    """
    # Merge all clipped anthropogenic feature layers
    merged_features = arcpy.Merge_management(file_list, out_name)
    arcpy.AddMessage('Merge completed')

    return merged_features


def RenameFeatureClass(in_data, out_data):
    """
    Deletes existing layers and feature classes of the out_data name and
    renames provided feature class. Provided feature class may not have
    the same name as the out_data. The in_data will be deleted.
    :param in_data: a feature class
    :param out_data: the name to save the output as a string
    :return: the name of the output as a string
    """
    # Delete any existing instances of the file to be overwritten
    # Delete layers in the TOC
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        m = p.activeMap
        try:
            for layer in m.listLayers(out_data):
                arcpy.Delete_management(layer)
            for feature in arcpy.ListFeatureClasses(out_data):
                arcpy.Delete_management(feature)
        except arcpy.ExecuteError:
            arcpy.AddMessage("Renaming failed to delete existing feature")
    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        try:
            for layer in arcpy.mapping.ListLayers(mxd, out_data):
                arcpy.Delete_management(layer)
            # Delete feature classes in the geodatabase
            for feature in arcpy.ListFeatureClasses(out_data):
                arcpy.Delete_management(feature)
        except arcpy.ExecuteError:
            arcpy.AddMessage("Renaming failed to delete existing feature")
    # Execute renaming
    out_fc = arcpy.CopyFeatures_management(in_data, out_data)
    arcpy.Delete_management(in_data)

    return out_fc


def RemoveFeatures(file_list, out_name):
    """
    Intersects the provided feature classes and, if overlapping features
    exist, unions the overlapping features with the first feature class,
    selects the overlapping features, and deletes those features. If no
    overlap exists, creates a copy of the first feature class saved as
    the out_name.
    :param file_list: a list of feature classes where overlapping features
    will be removed from the first feature classw
    :param out_name: a name to save the output, as a string
    :return: the name of the feature class with the remaining features
    as a string, the name of the overlapping feature as a string. 
    The overlap feature class is used to remove from the proposed surface
    disturbance any previously-disturbed surface by Debit Tool 4 in ID HQT.
    """
    # Remove features that will be updated
    overlap = arcpy.Intersect_analysis(file_list, "overlap")

    test = arcpy.GetCount_management(overlap)
    count = int(test.getOutput(0))

    if count > 0:
        # Union the first provided feature class with the result
        # of the intersect (i.e., overlapping features)
        union = arcpy.Union_analysis([file_list[0], overlap], "union")

        # Select from the union features identical to the overlap
        # and delete from the first provided feature class
        selected = arcpy.MakeFeatureLayer_management(union, "union_lyr")
        arcpy.SelectLayerByLocation_management(selected,
                                               "ARE_IDENTICAL_TO",
                                               overlap)
        arcpy.DeleteFeatures_management(selected)

        # Save the output as the out_name
        remaining_features = arcpy.CopyFeatures_management(selected,
                                                           out_name)

        arcpy.Delete_management("union")

    else:
        # Update message
        arcpy.AddMessage("No overlapping features identified")

        # Return None for overlap
        overlap = None

        # Make a copy of the first provided feature class
        remaining_features = arcpy.CopyFeatures_management(file_list[0],
                                                           out_name)

    # arcpy.Delete_management("overlap")

    return remaining_features, overlap


def SimplifyFields(input_features, allowable_fields):
    """
    Uses the dissolve tool to simplify the fields in the attribute
    table of the provided feature class.
    :param input_features: feature class with attribute table to be
    simplified
    :param allowable_fields: fields to remain in simplified feature
    class's attribute table
    :return: None
    """
    # Create a local copy to allow overwriting
    in_data = input_features
    temp_copy = "in_memory/tmpFC"
    arcpy.CopyFeatures_management(in_data, temp_copy)

    # Dissolve features
    in_features = temp_copy
    out_feature_class = input_features
    dissolve_fields = []
    for field in arcpy.ListFields(in_features):
        if (field.name in allowable_fields 
            and field.editable == True 
            and field.type != 'Geometry'):
            dissolve_fields.append(field.name)
    arcpy.Dissolve_management(in_features, out_feature_class, dissolve_fields)

    # Clean up
    arcpy.Delete_management("in_memory")
