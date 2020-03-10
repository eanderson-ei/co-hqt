"""
Name:     DebitTool_1.py
Author:   Erik Anderson
Created:  Dececmber 18, 2018
Revised:  February 25, 2019
Version:  Created using Python 3.6.3, Arc version 10.4.1
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
    Provided_Disturbance = arcpy.GetParameterAsText(1)
    includes_anthro_mod = arcpy.GetParameterAsText(2)  # optional
    Proposed_Modified_Features_Provided = arcpy.GetParameterAsText(3)  # optional

    # Update boolean parameters
    includes_anthro_mod = util.Str2Bool(includes_anthro_mod)

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    arcpy.AddMessage("Python version: " + sys.version)

    # Instantiate an cheStandard object
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
    # Filenames for feature classes and rasters created by this script
    PROPOSED_SURFACE_DISTURBANCE_DEBITS = "Proposed_Surface_Disturbance_Debits"
    PROPOSED_MODIFIED_FEATURES = "Proposed_Modified_Features"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    
    # Update includes_anthro_mod if Proposed_Modified_Features is
    # provided
    if Proposed_Modified_Features_Provided and not includes_anthro_mod:
        includes_anthro_mod = True

    # Check input features for existence of features and feature type;
    # create template if Proposed_Surface_Disturbance is not provided
    if Provided_Disturbance:
        # Check provided input
        hqtlib.CheckPolygonInput(Provided_Disturbance)

        # Create a local copy of the provided disturbance in case it is
        # the output of the projected input from re-running Debit Tool 1
        PSD_copy = arcpy.CopyFeatures_management(Provided_Disturbance,
                                                 "in_memory/PSD_provided")

        # Update message
        arcpy.AddMessage("Projecting provided feature(s) to "
                         + coordinate_system.name)

        # Project input to standard coordinate system
        inputFeature = PSD_copy
        out_name = PROPOSED_SURFACE_DISTURBANCE_DEBITS
        Proposed_Surface_Disturbance = hqtlib.ProjectInput(
            inputFeature, out_name, coordinate_system
            )
        zoom_to = True

    else:
        # Update message
        arcpy.AddMessage("Creating template for digitizing proposed "
                         "surface disturbance \nDigitize features in "
                         "feature class named "
                         "Proposed_Surface_Disturbance_Debits created within "
                         "the project's unique geodatabase")

        # Create a template
        out_name = PROPOSED_SURFACE_DISTURBANCE_DEBITS
        Proposed_Surface_Disturbance = util.CreateTemplate(
            projectGDB, out_name, coordinate_system
            )
        zoom_to = False

    if includes_anthro_mod:
        # Create a template for digitizing anthropogenic features proposed for
        # modification
        out_name = "Proposed_Modified_Features_tmp"
        Template_Features = util.CreateTemplate(
            projectGDB, out_name, coordinate_system
            )

        if Proposed_Modified_Features_Provided:
            # Do not zoom to proposed surface disturbance
            zoom_to = False

            # Merge with the provided layer, if provided
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

        else:
            # Save the template as Proposed_Modified_Features
            in_data = Template_Features
            out_data = PROPOSED_MODIFIED_FEATURES
            Proposed_Modified_Features = util.RenameFeatureClass(
                in_data, out_data
                )
        
        # Update message
        arcpy.AddMessage("Adding fields Type and Subtype to "
                         "the Proposed_Modified_Features layer")

        # Add fields Type and Subtype
        inputFeature = Proposed_Modified_Features
        fieldsToAdd = ["Type", "Subtype"]
        fieldTypes = ["TEXT", "TEXT"]
        util.AddFields(inputFeature, fieldsToAdd, fieldTypes,
                         copy_existing=True)

        # Clean up
        arcpy.Delete_management(Template_Features)

        # Create Domain for Subtype attributes and assign to Subtype field
        featureList = [Proposed_Modified_Features]
        util.AddSubtypeDomains(featureList, projectGDB, parameter_values)

        # Add layer to map for editing
        layerFile = cheStandard.getLayerFile("ProposedSurfaceDisturbance.lyr")
        util.AddToMap(Proposed_Modified_Features, layerFile)

    # Add layer to map document
    layerFile = cheStandard.getLayerFile("ProposedSurfaceDisturbance.lyr")
    util.AddToMap(Proposed_Surface_Disturbance, layerFile, zoom_to)

    # Update message
    arcpy.AddMessage("Adding fields to Proposed_Surface_Disturbance")

    # Add fields for Type, Subtype, Surface Disturbance, and Reclassifed Subtype
    input_feature = Proposed_Surface_Disturbance
    fields = ["Type", "Subtype", "Surface_Disturbance",
              "Reclassified_Subtype"]
    fieldTypes = ["TEXT", "TEXT", "TEXT", "TEXT"]
    util.AddFields(input_feature, fields, fieldTypes,
                   copy_existing=True)

    # Add Domains to Proposed_Surface_Disturbance_Debits layer
    featureList = [Proposed_Surface_Disturbance]
    domain_name = "Type"
    code_list = [row[0] for row in arcpy.da.SearchCursor(
        parameter_values, "Type")]

    # Create Domain for Subtype attributes and assign to Subtype field
    util.AddSubtypeDomains(featureList, projectGDB, parameter_values)

    # Create Domain for Type attributes and assign to Type field
    util.AddCodedTextDomain(featureList, projectGDB, domain_name, code_list)

    # Create Domain for Type attributes and assign to Surface Disturbance field
    domain_name = "Surface_Disturbance"
    code_list = ["Term_Reclaimed", "Term_Retired", "Term_Reclassified",
                 "Permanent"]
    util.AddCodedTextDomain(featureList, projectGDB, domain_name, code_list)

    # Create Domain for Type attributes and assign to Reclassified Subtype
    # field
    domain_name = "Reclassified_Subtype"
    code_list = [row[0] for row in arcpy.da.SearchCursor(
        parameter_values, "Subtype")]
    util.AddCodedTextDomain(featureList, projectGDB, domain_name, code_list)

    if includes_anthro_mod:
        # Extend type domain to Proposed_Modified_Features
        try:
            arcpy.AssignDomainToField_management(Proposed_Modified_Features,
                                                 "Type", "Type")
        except arcpy.ExecuteError:
            arcpy.AddMessage("Type domain not updated for "
                             "Proposed_Modified_Features")

    # Save map document and exit
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
