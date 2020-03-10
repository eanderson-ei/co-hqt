"""
Name:     DebitTool_4.py
Author:   Erik Anderson
Created:  Dececmber 18, 2018
Revised:  February 25, 2019
Version:  Created using Python 3.6.3, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better
          Spatial Analyst Extension

Path to the project's workspace is derived from the Map_Units
feature class provided by the user.
Requires Proposed_Surface_Disturbance_Debits, Disturbed_Footprint, and
Map_Units feature classes created by Debit Tool 2.

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
import gc
import hqtlib
import util
import cohqt
from arcpy.sa import Con, IsNull, Float, Raster

if arcpy.ListInstallations()[0] == 'arcgispro':  # switch
    import importlib
    importlib.reload(hqtlib) #ensures up-to-date hqtlib runs on arcpro
    importlib.reload(util)
    importlib.reload(cohqt)


def main():
    # GET PARAMETER VALUES
    Map_Units_Provided = arcpy.GetParameterAsText(0)

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
        arcpy.CreateFolder_management(scratch_folder)
    arcpy.env.scratchWorkspace = scratch_folder
    # Overwrite outputs
    arcpy.env.overwriteOutput = True

    # DEFINE GLOBAL VARIABLES
    cell_size = 30
    inputDataPath = cheStandard.InputDataPath
    GrSG_Habitat = cheStandard.GrSGHabitatRaster
    ConiferModifier = cheStandard.ConiferModifier
    GrSG_LDI = cheStandard.GrSG_LDI
    LekPresenceRaster = cheStandard.LekPresenceRaster
    Lek_Distance_Modifier = cheStandard.LekDistanceModifier
    SageModifier = cheStandard.SageModifier
    GrSG_Habitat = cheStandard.BWSGHab
    
    
    
    # Filenames of feature classes and rasters used by this script
    MAP_UNITS = "Map_Units"
    PROPOSED_SURFACE_DISTURBANCE_DEBITS = "Proposed_Surface_Disturbance_Debits"
    DISTURBED_FOOTPRINT = "Disturbed_Footprint"
    CURRENT_ANTHRO_FEATURES = "Current_Anthro_Features"
    CURRENT_ANTHRO_DISTURBANCE = "GrSG_Pre_Anthro_Disturbance"
    PROJECTED_ANTHRO_DISTURBANCE = "GRSG_Post_Anthro_Disturbance"
    LEK_DISTURBANCE_MODIFIER = "Lek_Disturbance_Modifier"
    DEBIT_PROJECT_AREA = "Debit_Project_Area"
    DEBIT_PROJECT_IMPACT_A = "Debit_Project_Impact_Adjusted"
    
    # Filenames of feature classes and rasters created by this script
    # GrSG Filenames
    GRSG_PRE_BREEDING_A = "GRSG_Pre_Breeding_adjusted"
    GRSG_PRE_SUMMER_A = "GRSG_Pre_Summer_adjusted"
    GRSG_PRE_WINTER_A = "GRSG_Pre_Winter_adjusted"
    GRSG_POST_BREEDING_A = "GRSG_Post_Breeding_adjusted"
    GRSG_POST_SUMMER_A = "GRSG_Post_Summer_adjusted"
    GRSG_POST_WINTER_A = "GRSG_Post_Winter_adjusted"
    CUMULATIVE_MODIFIER_PRE_A = "GRSG_Pre_Cumulative_Modifier_adjusted"
    CUMULATIVE_MODIFIER_POST_A = "GRSG_Post_Cumulative_Modifier_adjusted"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    # Check out Spatial Analyst extension
    hqtlib.CheckOutSpatialAnalyst()

    # Clear selection, if present
    util.ClearSelectedFeatures(Map_Units_Provided)

    # Check Map_Units layer
    feature = Map_Units_Provided
    required_fields = ["Map_Unit_ID", "Map_Unit_Name"]
    no_null_fields = ["Map_Unit_ID"]
    expected_fcs = None
    hqtlib.CheckPolygonInput(feature, required_fields, expected_fcs,
                            no_null_fields)

    # Update Map Units layer with provided layer and add to map
    Map_Units = util.AdoptParameter(Map_Units_Provided, MAP_UNITS,
                                     preserve_existing=False)
    layerFile = cheStandard.getLayerFile("MapUnits.lyr")
    util.AddToMap(Map_Units, layerFile)

    # # Udpate message
    # arcpy.AddMessage("Dissolving all multi-part map units to create "
    #                  "Map_Units_Dissolve")

    # # Dissolve Map Units
    # allowable_fields = ["Map_Unit_ID", "Map_Unit_Name", "Notes",
    #                     "Disturbance_Type", "Precip", ]
    # out_name = MAP_UNITS_DISSOLVE
    # anthro_features = CURRENT_ANTHRO_FEATURES
    # Map_Units_Dissolve = hqtlib.DissolveMapUnits(MUs, allowable_fields,
    #                                             out_name, anthro_features)

    # # Update message
    # arcpy.AddMessage("Adding Map_Units_Dissolve to map")

    # # Add layer to map document
    # feature = Map_Units_Dissolve
    # layerFile = cheStandard.getLayerFile("Map_Units.lyr")
    # util.AddToMap(feature, layerFile)

    # # Update message
    # arcpy.AddMessage("Calculating area in acres for each map unit")

    # # Calculate Area
    # hqtlib.CalcAcres(Map_Units_Dissolve)
    
    # Update message
    arcpy.AddMessage("Creating site-scale habitat quality rasters")
    
    # # ADD Join from Excel Doc
    # out_table = os.path.join(projectGDB, "Site_Scale_Scores")
    # summary_table = arcpy.ExcelToTable_conversion(Debit_Calculator,
    #                                               out_table,
    #                                               "Summary")
    
    # arcpy.AddJoin_management(Map_Units, "Map_Unit_ID",
    #                          summary_table, "MapUnitID")
    
    
    # Convert Map Units to raster of Habitat Quality (0 - 1 scale) and  mask
    # out BWSG habitat
    seasonsList = cheStandard.GrSGSeasons
    for season in seasonsList:
        mu_raster_path = cohqt.convertMapUnitsToRaster(projectGDB, 
                                                       Map_Units, 
                                                       season, 
                                                       cell_size)
        mu_raster = Raster(mu_raster_path)
        # Mask out BWSG habitat
        SuitableHabitat_adjusted = Con(IsNull(Float(mu_raster)), 
                                       GrSG_Habitat, 
                                       Float(mu_raster))
        SuitableHabitat_adjusted.save(os.path.join(
            projectGDB, season + "_Habitat_adjusted")
                                      )
    
    # Update message
    arcpy.AddMessage("Calculating Pre-Project Habitat Modifiers")
    
    # Re-run fron calcWinterHabitat down with updated BWSG layer (append 
    # "_adjusted")
    
    WinterSuitableHabitat = os.path.join(projectGDB, 
                                         "Winter_Habitat_adjusted")
    winterHabitatPre = cohqt.calcWinterHabitatGRSG(
        CURRENT_ANTHRO_DISTURBANCE,
        ConiferModifier,
        GrSG_LDI,
        WinterSuitableHabitat
        )
    LSDMWinterPre = cohqt.applyLekUpliftModifierPre(
        winterHabitatPre,
        LekPresenceRaster
        )
    
    BreedingSuitableHabitat = os.path.join(projectGDB, 
                                           "Breed_Habitat_adjusted")
    breedingHabitatPre = cohqt.calcBreedingHabitatGRSG(
        CURRENT_ANTHRO_DISTURBANCE,
        ConiferModifier,
        GrSG_LDI,
        Lek_Distance_Modifier,
        BreedingSuitableHabitat
        )
    LSDMBreedingPre = cohqt.applyLekUpliftModifierPre(
        breedingHabitatPre,
        LekPresenceRaster
        )
    
    SummerSuitableHabitat = os.path.join(projectGDB,
                                         "Summer_Habitat_adjusted")
    summerHabitatPre = cohqt.calcSummerHabitatGRSG(
        CURRENT_ANTHRO_DISTURBANCE,
        ConiferModifier,
        GrSG_LDI,
        SageModifier,
        SummerSuitableHabitat
        )
    LSDMSummerPre = cohqt.applyLekUpliftModifierPre(
        summerHabitatPre,
        LekPresenceRaster
        )
    
    seasonalHabitatRasters = [LSDMWinterPre, LSDMBreedingPre, LSDMSummerPre]
    
    # Save outputs
    # winterHabitatPre.save("Pre_Seasonal_Winter_adjusted")
    LSDMWinterPre.save(GRSG_PRE_WINTER_A)
    # breedingHabitatPre.save("Pre_Seasonal_Breeding_adjusted")
    LSDMBreedingPre.save(GRSG_PRE_BREEDING_A)
    # summerHabitatPre.save("Pre_Seasonal_Summer_adjusted")
    LSDMSummerPre.save(GRSG_PRE_SUMMER_A)
    
    # Calculate average of three seasonal habitat rasters pre-project
    finalPreCumulative = cohqt.calcAverageHabitatQuality(
        seasonalHabitatRasters
    )
    finalPreCumulative.save(CUMULATIVE_MODIFIER_PRE_A)
        
    # Calculate post-project cumulative habtiat modifiers
    winterHabitatPost = cohqt.calcWinterHabitatGRSG(
        PROJECTED_ANTHRO_DISTURBANCE,
        ConiferModifier,
        GrSG_LDI,
        WinterSuitableHabitat
        )
    LSDMWinterPost = cohqt.applyLekUpliftModifierPost(
        winterHabitatPost,
        LekPresenceRaster,
        LEK_DISTURBANCE_MODIFIER
        )
    breedingHabitatPost = cohqt.calcBreedingHabitatGRSG(
        PROJECTED_ANTHRO_DISTURBANCE,
        ConiferModifier,
        GrSG_LDI,
        Lek_Distance_Modifier,
        BreedingSuitableHabitat
        )
    LSDMBreedingPost = cohqt.applyLekUpliftModifierPost(
        breedingHabitatPost,
        LekPresenceRaster,
        LEK_DISTURBANCE_MODIFIER
        )
    summerHabitatPost = cohqt.calcSummerHabitatGRSG(
        PROJECTED_ANTHRO_DISTURBANCE,
        ConiferModifier,
        GrSG_LDI,
        SageModifier,
        SummerSuitableHabitat
        )
    LSDMSummerPost = cohqt.applyLekUpliftModifierPost(
        summerHabitatPost,
        LekPresenceRaster,
        LEK_DISTURBANCE_MODIFIER
        )

    seasonalHabitatRasters = [LSDMWinterPost, LSDMBreedingPost, LSDMSummerPost]

    # Save outputs
    # winterHabitatPost.save("Post_Seasonal_Winter")
    LSDMWinterPost.save(GRSG_POST_WINTER_A)
    # breedingHabitatPost.save("Post_Seasonal_Breeding")
    LSDMBreedingPost.save(GRSG_POST_BREEDING_A)
    # summerHabitatPost.save("Post_Seasonal_Summer")
    LSDMSummerPost.save(GRSG_POST_SUMMER_A)

    # Calculate average of three seasonal habitat rasters post-project
    finalPostCumulative = cohqt.calcAverageHabitatQuality(
        seasonalHabitatRasters
    )
    finalPostCumulative.save(CUMULATIVE_MODIFIER_POST_A)
    
    # Calculate Zonal Statistics for cumulative modifier rasters
    # Calculate zonal statistics for pre-project
    inZoneData = DEBIT_PROJECT_AREA
    inValueRaster = finalPreCumulative
    zoneField = "ZONAL"
    outTable = "GRSG_Stats_Pre_adjusted"
    hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

    # Join the zonal statistic to the Debit Project Area table
    fieldName = "GRSG_Pre_Project_A"
    hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

    # Calculate zonal statistics for post-project
    inZoneData = DEBIT_PROJECT_AREA
    inValueRaster = finalPostCumulative
    zoneField = "ZONAL"
    outTable = "GRSG_Stats_Post_adjusted"
    hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

    # Join the zonal statistic to the Debit Project Area table
    fieldName = "GrSG_Post_Project_A"
    hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

    # Calculate debits using field data
    cohqt.calcDebits(DEBIT_PROJECT_AREA, "GRSG_Pre_Project_A",
                     "GrSG_Post_Project_A", "Debits_adj")
    
    # Update message
    arcpy.AddMessage("Creating visualization of impact from debit project")

    # Calculate impact intensity for debit project
    debit_impact = cohqt.calcImpact(finalPreCumulative, finalPostCumulative)
    debit_impact.save(DEBIT_PROJECT_IMPACT_A)

    # Add Debit Impact raster to map and save map document
    feature = debit_impact
    layerFile = cheStandard.getLayerFile("DebitProjectImpact.lyr")
    util.AddToMap(feature, layerFile, zoom_to=True)
    
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
