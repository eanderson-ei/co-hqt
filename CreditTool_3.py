"""
Name:     CreditTool_3.py
Author:   Erik Anderson
Created:  April 25, 2019
Revised:  April 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better;
          Spatial Analyst extension

The provided Map_Units_Dissolve feature class is used to derive the workspace,
but the Map_Units_Dissolve feature class in the gdb is used afterwards.
Requires Map_Units_Dissolve feature classes created by Credit Tool 3.
Transects_Provided should be created using a spatially balanced sample design.

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
import os
import hqtlib
import util

if arcpy.ListInstallations()[0] == 'arcgispro':  # switch
    import importlib
    importlib.reload(hqtlib) #ensures up-to-date hqtlib runs on arcpro
    importlib.reload(util)


def main():
    # GET PARAMETER VALUES
    Map_Units_Dissolve_Provided = arcpy.GetParameterAsText(0)
    Transects_Provided = arcpy.GetParameterAsText(1)  # optional
    Project_Folder = arcpy.GetParameterAsText(2)
    Project_Name = arcpy.GetParameterAsText(3)  # optional

    # DEFINE DIRECTORIES & PATH NAMES FOR FOLDERS & GBDs
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    # Construct pathname to workspace
    projectGDB = arcpy.Describe(Map_Units_Dissolve_Provided).path
    arcpy.AddMessage("Project geodatabase: " + projectGDB)

    # ENVIRONMENT SETTINGS
    # Set workspaces
    arcpy.env.workspace = projectGDB
    scratch_folder = os.path.join(
        arcpy.Describe(projectGDB).path, 'scratch'
        )
    if arcpy.Exists(scratch_folder):
        pass
    else:
        arcpy.CreateFolder_management(arcpy.Describe(projectGDB).path, 'scratch')
    arcpy.env.scratchWorkspace = scratch_folder
    # Overwrite outputs
    arcpy.env.overwriteOutput = True

    # DEFINE GLOBAL VARIABLES
    # Filenames for feature classes or rasters used by this script
    MAP_UNITS_DISSOLVE = "Map_Units_Dissolve"
    # Filenames for feature classes or rasters created by this script
    TRANSECTS_SJ = "Transects_SpatialJoin"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    if Transects_Provided:
        # Update message
        arcpy.AddMessage("Executing spatial join of Transects and "
                         "Map_Unit_Dissolve layer")

        # hqtlib.AddTransectFields(Transects)
        Map_Units_Dissolve = MAP_UNITS_DISSOLVE
        out_name = TRANSECTS_SJ
        hqtlib.TransectJoin(Map_Units_Dissolve, Transects_Provided, out_name)

    else:
        # arcpy.AddError("ERROR:: Please provide the transects feature "
        #                "class or shapefile. See User's Guide.")
        # sys.exit(0)

        # Check out Spatial Analyst extension
        hqtlib.CheckOutSpatialAnalyst()
        
        # Check Map_Units_Dissolve layer
        required_fields = ["Transects"]
        no_null_fields = ["Transects"]
        expected_fcs = None
        hqtlib.CheckPolygonInput(Map_Units_Dissolve_Provided, required_fields,
                                    expected_fcs, no_null_fields)
        
        Map_Units = Map_Units_Dissolve_Provided
        field_name = "Transects"
        out_name = "Transects"
        transects = hqtlib.GenerateTransects(projectGDB, Map_Units,
                                             field_name, out_name) ##swapped "workspace" for "project GDB"
        hqtlib.AddTransectFields(transects)
    
        # Identify the map unit associated with each transect
        hqtlib.TransectJoin(MAP_UNITS_DISSOLVE, transects, TRANSECTS_SJ)

    # Remove unnecessary fields
    allowable_fields = ["Bearing1", "Bearing2", "Bearing3", "UTM_E", "UTM_N",
                        "Map_Unit_ID", "Map_Unit_Name", "Indirect",
                        "Acres", "PropLek", "PropMesic",
                        "Current_Breed", "Current_Summer",
                        "Current_Winter", "Projected_Breed",
                        "Projected_Summer", "Projected_Winter", "Permanent_Breed",
                        "Permanent_Summer", "Permanent_Winter", "Transects"]
    util.SimplifyFields(TRANSECTS_SJ, allowable_fields)

    # Add Transects to map
    util.AddToMap(TRANSECTS_SJ)

    # Export data to Excel
    table = TRANSECTS_SJ
    hqtlib.ExportToExcel(table, Project_Folder, Project_Name)

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
