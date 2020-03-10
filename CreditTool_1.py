"""
Name:     CreditTool_1.py
Author:   Erik Anderson
Created:  April 25, 2019
Revised:  April 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better

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
import sys
import gc
import hqtlib
import util
import cohqt

if arcpy.ListInstallations()[0] == 'arcgispro':  # switch
    import importlib
    importlib.reload(hqtlib) #ensures up-to-date hqtlib runs on arcpro
    importlib.reload(util)
    importlib.reload(cohqt)


def main():
    # GET PARAMETER VALUES
    projectGDB = arcpy.GetParameterAsText(0)
    Credit_Project_Boundary = arcpy.GetParameterAsText(1)
    includes_Conifer_Treatment = arcpy.GetParameterAsText(2)  # optional
    Conifer_Treatment_Area_Provided = arcpy.GetParameterAsText(3)  # optional
    includes_anthro_mod = arcpy.GetParameterAsText(4)  # optional
    Proposed_Modified_Features_Provided = arcpy.GetParameterAsText(5)  # optional

    # Update boolean parameters
    includes_anthro_mod = util.Str2Bool(includes_anthro_mod)

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    arcpy.AddMessage("Python version: " + sys.version)
    # Instantiate a cheStandard object
    cheStandard = cohqt.cheStandard(projectGDB, scriptPath)

    # ENVIRONMENT SETTINGS
    # Set workspaces
    arcpy.env.workspace = projectGDB
    arcpy.env.scratchWorkspace = projectGDB
    # Overwrite outputs
    arcpy.env.overwriteOutput = True

    # DEFINE GLOBAL VARIABLES
    parameter_values = cheStandard.ParameterValues
    coordinate_system = cheStandard.CoorSystem
    habitat_bounds = cheStandard.HabitatMgmtArea
    # File names for feature classes and rasters created by this script
    CREDIT_PROJECT_AREA = "Credit_Project_Area"
    CONIFER_TREATMENT_AREA = "Conifer_Treatment_Area"
    PROPOSED_MODIFIED_FEATURES = "Proposed_Modified_Features"
    MAP_UNITS = "Map_Units"
    
    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    # Update includes_anthro_mod if Proposed_Modified_Features is
    # provided
    if Proposed_Modified_Features_Provided and not includes_anthro_mod:
        includes_anthro_mod = True

    # Update includes_conifer_treatment if Conifer Treatment Area
    # provided
    if Conifer_Treatment_Area_Provided and not includes_Conifer_Treatment:
        includes_Conifer_Treatment = True

    # Exit with warning if no Credit Project Boundary is provided and project
    # is does not propose to remove or modify anthropogenic disturbance
    if not Credit_Project_Boundary and not includes_anthro_mod:
        arcpy.AddError("ERROR:: A credit project boundary must be provided "
                       "unless the project proposes to remove or modify "
                       "anthropogenic features. Ensure 'Credit Project will "
                       "remove or modify existing anthropogenic features' is "
                       "checked if true. Please see the User's Guide for "
                       "additional instruction.")
        sys.exit(0)

    # Check input features
    if Credit_Project_Boundary:
        # Check provided input for polygon shape type
        hqtlib.CheckPolygonInput(Credit_Project_Boundary)

    if includes_Conifer_Treatment:
        # Check provided input for polygon shape type
        hqtlib.CheckPolygonInput(Conifer_Treatment_Area_Provided)

    if Proposed_Modified_Features_Provided:
        # Check provided feature for polygon shape type
        hqtlib.CheckPolygonInput(Proposed_Modified_Features_Provided)

    # Set up zoom to for map units variable
    zoom_to_mu = False

    # Check input features for existence of features and feature type;
    # create template if Credit_Project_Boundary is not provided
    if Credit_Project_Boundary:
        # Create a local copy of the credit project boundary in case it is
        # the output of the projected input from re-running Credit Tool 1
        CPB_copy = arcpy.CopyFeatures_management(Credit_Project_Boundary,
                                                 "in_memory/CPB_provided")

        # Update message
        arcpy.AddMessage("Projecting provided feature(s) to "
                         + coordinate_system.name)
        
        # Project input to standard projection
        in_dataset = CPB_copy
        out_dataset = "Credit_Project_Boundary_Projected"
        projectedFeature = hqtlib.ProjectInput(in_dataset, out_dataset,
                                               coordinate_system)

        # Update message
        arcpy.AddMessage("Determining project area - eliminating areas of non-"
                         "habitat from the Project Area")

        # Eliminate areas of non-habitat from project boundary
        Project_Area = projectedFeature
        outName = "in_memory/Credit_Project_Boundary_Clipped"
        clippedFeature = hqtlib.EliminateNonHabitat(Project_Area, outName,
                                                    habitat_bounds)

        # Create Credit Project Area
        in_features = clippedFeature
        out_feature_class = CREDIT_PROJECT_AREA
        arcpy.Dissolve_management(in_features, out_feature_class)

        # Update message
        arcpy.AddMessage("Creating Map Units layer")

        # Create Map_Units layer
        in_data = clippedFeature
        out_data = MAP_UNITS
        Map_Units = hqtlib.CreateMapUnits(in_data, out_data)

        zoom_to_mu = True

        # Add Map_Units to map
        layerFile = cheStandard.getLayerFile("MapUnits.lyr")
        util.AddToMap(Map_Units, layerFile, zoom_to_mu)

    if includes_Conifer_Treatment:
        # Create a template for digitizing anthropogenic features proposed for
        # modification
        out_name = "Conifer_Treatment_Area_tmp"
        Template_Features = util.CreateTemplate(
            projectGDB, out_name, coordinate_system
        )

        # Set up zoom to for proposed surface disturbance variable
        zoom_to_cta = False

        if Conifer_Treatment_Area_Provided:
            # Merge the template created with the provided layer, if provided
            fileList = [Conifer_Treatment_Area_Provided,
                        Template_Features]
            out_name = "in_memory/tmp_Conifer"
            merged_features = util.MergeFeatures(fileList, out_name)

            # Rename the provided as merged (cannot merge two files with
            # equivalent filenames) as Conifer_Treatment_Area
            in_data = merged_features
            out_data = CONIFER_TREATMENT_AREA
            Conifer_Treatment_Area = arcpy.CopyFeatures_management(
                in_data, out_data
            )

            zoom_to_cta = True

        else:
            # Save the template as Conifer_Treatment_Area
            in_data = Template_Features
            out_data = CONIFER_TREATMENT_AREA
            Conifer_Treatment_Area = util.RenameFeatureClass(
                in_data, out_data
            )

        # Clean up
        arcpy.Delete_management("Conifer_Treatment_Area_tmp")

        # Add layer to map for editing
        util.AddToMap(Conifer_Treatment_Area, zoom_to=zoom_to_cta)

    if includes_anthro_mod:
        # Create a template for digitizing anthropogenic features proposed for
        # modification
        out_name = "Proposed_Modified_Features_tmp"
        Template_Features = util.CreateTemplate(
            projectGDB, out_name, coordinate_system
            )

        # Update message
        arcpy.AddMessage("Adding fields Type and Subtype to "
                         "the Proposed_Modified_Features layer")

        # Add fields Type and Subtype
        inputFeature = Template_Features
        fieldsToAdd = ["Type", "Subtype"]
        fieldTypes = ["TEXT", "TEXT"]
        util.AddFields(inputFeature, fieldsToAdd, fieldTypes,
                         copy_existing=True)

        # Set up zoom to for proposed surface disturbance variable
        zoom_to_psd = False

        if Proposed_Modified_Features_Provided:
            # Merge the template created with the provided layer, if provided
            fileList = [Proposed_Modified_Features_Provided,
                        Template_Features]
            out_name = "in_memory/tmp_Modified"
            merged_features = util.MergeFeatures(fileList, out_name)

            # Rename the provided as merged (cannot merge two files with
            # equivalent filenames) as Proposed_Modified_Features
            in_data = merged_features
            out_data = PROPOSED_MODIFIED_FEATURES
            Proposed_Modified_Features = arcpy.CopyFeatures_management(
                in_data, out_data
                )

            zoom_to_psd = True

        else:
            # Save the template as Proposed_Modified_Features
            in_data = Template_Features
            out_data = PROPOSED_MODIFIED_FEATURES
            Proposed_Modified_Features = util.RenameFeatureClass(
                in_data, out_data
                )

        # Clean up
        arcpy.Delete_management("Proposed_Modified_Features_tmp")

        # Add Domains to Proposed_Modified_Features layer
        featureList = [Proposed_Modified_Features]
        # Create Domain for Subtype attributes and assign to Subtype field
        util.AddSubtypeDomains(featureList, projectGDB, parameter_values)
        
        # Create Domain for Type attributes and assign to Type field
        typeList = [row[0] for row in arcpy.da.SearchCursor(
                    parameter_values, "Type")]
        util.AddCodedTextDomain(featureList, projectGDB, "Type", typeList)

        # Add layer to map for editing
        layerFile = cheStandard.getLayerFile("DebitProjectArea.lyr")
        util.AddToMap(Proposed_Modified_Features, layerFile, zoom_to_psd)

        if not Credit_Project_Boundary:
            # Create dummy Map Units layer if no Credit Project Boundary provided
            out_name = MAP_UNITS
            Map_Units = util.CreateTemplate(projectGDB, out_name,
                                              coordinate_system)

            if Proposed_Modified_Features_Provided:
                # Zoom to the Modified Anthro Feature layer
                if arcpy.ListInstallations()[0] == 'arcgispro':
                    p = arcpy.mp.ArcGISProject("CURRENT")
                    m = p.activeMap
                    layer=m.Layer(PROPOSED_MODIFIED_FEATURES)
                    pass
                    # df.extent = layer.getSelectedExtent()
                else:
                    mxd = arcpy.mapping.MapDocument("CURRENT")
                    df = mxd.activeDataFrame
                    layer = arcpy.mapping.Layer(PROPOSED_MODIFIED_FEATURES)
                    df.extent = layer.getSelectedExtent()

    # Add fields Map_Unit_ID, Map_Unit_Name, and Meadow to Map_Units
    fields = ["Map_Unit_ID", "Map_Unit_Name", "Notes"]
    fieldTypes = ["SHORT", "TEXT", "TEXT"]
    util.AddFields(Map_Units, fields, fieldTypes, copy_existing=True)

    # Add Domains to Map_Units layer
    # Create Domain for Map_Unit_ID attributes
    domainName = "Map_Unit_ID"
    range_low = 0
    range_high = 10000
    util.AddRangeDomain(Map_Units, projectGDB,
                          domainName, range_low, range_high)

    # Clean up
    arcpy.Delete_management("in_memory")

    # Save map document
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        p.save()
    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        mxd.save()
        
    # ------------------------------------------------------------------------
    
# EXECUTE SCRIPT


if __name__ == "__main__":
    gc.enable()
    main()
    gc.collect()
