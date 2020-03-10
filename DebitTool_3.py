"""
Name:     DebitTool_3.py
Author:   Erik Anderson
Created:  April 25, 2019
Revised:  April 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better;
          Spatial Analyst extension

The provided Map_Units feature class is used to derive the workspace.
Requires Map_Units feature classes created by Debit Tool 2.
Transects_Provided should be created using a spatially balanced sample design.

"""

# Import system modules
import arcpy
import sys
import gc
import hqtlib
import cohqt
import util
import os

if arcpy.ListInstallations()[0] == 'arcgispro':  # switch
    import importlib
    importlib.reload(hqtlib) #ensures up-to-date hqtlib runs on arcpro
    importlib.reload(util)
    importlib.reload(cohqt)


def main():
    # GET PARAMETER VALUES
    Map_Units_Provided = arcpy.GetParameterAsText(0)
    Transects_Provided = arcpy.GetParameterAsText(1)  # optional
    Project_Folder = arcpy.GetParameterAsText(2)
    Project_Name = arcpy.GetParameterAsText(3)  # optional

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    arcpy.AddMessage("Python version: " + sys.version)
    # Construct pathname to workspace
    projectGDB = arcpy.Describe(Map_Units_Provided).path
    arcpy.AddMessage("Project geodatabase: " + projectGDB)
    
    # Instantiate a idStandard object
    cheStandard = cohqt.cheStandard(projectGDB, scriptPath)

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
    MAP_UNITS = "Map_Units"
    
    # Filenames for feature classes or rasters created by this script
    TRANSECTS_SJ = "Transects_SpatialJoin"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    
    # Check Map_Units_Dissolve layer
    required_fields = ["Transects"]
    no_null_fields = None
    expected_fcs = None
    hqtlib.CheckPolygonInput(Map_Units_Provided, required_fields,
                                expected_fcs, no_null_fields)
    
    # Update Map Units layer with provided layer and add to map
    Map_Units = util.AdoptParameter(Map_Units_Provided, MAP_UNITS,
                                     preserve_existing=False)
    layerFile = cheStandard.getLayerFile("MapUnits.lyr")
    util.AddToMap(Map_Units, layerFile)
    
    if Transects_Provided:
        # Update message
        arcpy.AddMessage("Executing spatial join of Transects and "
                         "Map_Unit_Dissolve layer")

        out_name = TRANSECTS_SJ
        transects = Transects_Provided
        hqtlib.TransectJoin(Map_Units, transects, out_name)

    else:
        # arcpy.AddError("ERROR:: Please provide the transects feature"
        #                "class or shapefile provided by the SETT")
        # sys.exit(0)

        # Check out Spatial Analyst extension
        hqtlib.CheckOutSpatialAnalyst()        
        
        # Generate transects
        field_name = "Transects"
        out_name = "Transects"
        transects = hqtlib.GenerateTransects(projectGDB, Map_Units,
                                             field_name, out_name)
        
        # Add transect fields
        hqtlib.AddTransectFields(transects)
        util.AddToMap(out_name)
        
        # Identify the map unit associated with each transect
        out_name = TRANSECTS_SJ
        transects = transects
        hqtlib.TransectJoin(Map_Units, transects, out_name)

    # Remove unnecessary fields
    allowable_fields = ["Bearing1", "Bearing2", "Bearing3", 
                        "UTM_E", "UTM_N",
                        "Map_Unit_ID", "Map_Unit_Name", "Precip",
                        "Transects"]
    util.SimplifyFields(TRANSECTS_SJ, allowable_fields)

    # Add Transects to map
    util.AddToMap(TRANSECTS_SJ)

    # Export data to Excel
    table = TRANSECTS_SJ
    hqtlib.ExportToExcel(table, Project_Folder, Project_Name)
    
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
