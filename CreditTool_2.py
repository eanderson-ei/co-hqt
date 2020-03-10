"""
Name:     CreditTool_2.py
Author:   Erik Anderson
Created:  April 25, 2019
Revised:  April 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better
          Spatial Analyst extension

The provided Map_Units feature class is used to derive the workspace.
Requires Credit_Project_Area feature class created by Credit Tool 1 unless project
proposes to remove anthropogenic features.

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
import os
import gc
import hqtlib
import util
import cohqt
from arcpy.sa import Con

if arcpy.ListInstallations()[0] == 'arcgispro':  # switch
    import importlib
    importlib.reload(hqtlib) #ensures up-to-date hqtlib runs on arcpro
    importlib.reload(util)
    importlib.reload(cohqt)


def main():
    # GET PARAMETER VALUES
    Map_Units_Provided = arcpy.GetParameterAsText(0)  # optional
    Proposed_Modified_Features_Provided = arcpy.GetParameterAsText(1)  # optional
    Project_Name = arcpy.GetParameterAsText(2)

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    arcpy.AddMessage("Python version: " + sys.version)
    # Construct pathname to workspace
    if Map_Units_Provided:
        projectGDB = arcpy.Describe(Map_Units_Provided).path
    elif Proposed_Modified_Features_Provided:
        projectGDB = arcpy.Describe(Proposed_Modified_Features_Provided).path
    else:
        arcpy.AddMessage("Please provide either a Map_Units or " +
                         "Proposed_Modified_Features layer.")
        sys.exit(0)
    arcpy.AddMessage("Project geodatabase: " + projectGDB)
    Project_Folder = arcpy.Describe(projectGDB).path
    arcpy.AddMessage("Project folder:" + Project_Folder)
    
    # Instantiate a cheStandard object
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
        arcpy.CreateFolder_management( arcpy.Describe(projectGDB).path, 'scratch')
    arcpy.env.scratchWorkspace = scratch_folder
    # Overwrite outputs
    arcpy.env.overwriteOutput = True

    # DEFINE GLOBAL VARIABLES
    Parameter_Values = cheStandard.ParameterValues
    ConiferModifier = cheStandard.ConiferModifier
    GrSG_LDI = cheStandard.GrSG_LDI
    LekPresenceRaster = cheStandard.LekPresenceRaster
    Lek_Distance_Modifier = cheStandard.LekDistanceModifier
    SageModifier = cheStandard.SageModifier
    GrSG_Habitat = cheStandard.GrSGHabitatRaster
    MigrationModifier = cheStandard.MuleDeerMigrationMod
    WinterModifier = cheStandard.MuleDeerWinterMod
    SummerModifier = cheStandard.MuleDeerSummerMod
    MuleDeer_LDI = cheStandard.MuleDeerLDI
    emptyRaster = cheStandard.EmptyRaster
    BWMD_Open = cheStandard.BWMD_Open
    GrSG_Range = cheStandard.GrSGHabitat
    Mule_Range = cheStandard.MuleDeerHabitat
    cellSize = arcpy.GetRasterProperties_management(
        emptyRaster, "CELLSIZEX").getOutput(0)

    # Filenames for feature classes or rasters used by this script
    MAP_UNITS = "Map_Units"
    PROPOSED_MODIFIED_FEATURES = "Proposed_Modified_Features"
    CREDIT_PROJECT_AREA = "Credit_Project_Area"
    CONIFER_TREATMENT_AREA = "Conifer_Treatment_Area"

    # Filenames for feature class and rasters created by this script
    INDIRECT_IMPACT_AREA = "Indirect_Impact_Area"
    ANALYSIS_AREA = "Analysis_Area"
    MAP_UNITS_DISSOLVE = "Map_Units_Dissolve"
    # GrSG Filenames
    CURRENT_ANTHRO_DISTURBANCE = "GRSG_Pre_Anthro_Disturbance"
    PROJECTED_ANTHRO_DISTURBANCE = "GRSG_Post_Anthro_Disturbance"
    GRSG_PRE_BREEDING = "GRSG_Pre_Breeding"
    GRSG_PRE_SUMMER = "GRSG_Pre_Summer"
    GRSG_PRE_WINTER = "GRSG_Pre_Winter"
    GRSG_POST_BREEDING = "GRSG_Post_Breeding"
    GRSG_POST_SUMMER = "GRSG_Post_Summer"
    GRSG_POST_WINTER = "GRSG_Post_Winter"
    POST_CONIFER_MODIFIER= "Post_Conifer_Modifier"
    # Mule Deer Filenames
    CURRENT_ANTHRO_DISTURBANCE_MD = "MuleDeer_Pre_Anthro_Disturbance"
    PROJECTED_ANTHRO_DISTURBANCE_MD = "MuleDeer_Post_Anthro_Disturbance"
    MULE_PRE_SUMMER = "MuleDeer_Pre_Summer"
    MULE_PRE_MIGRATION = "MuleDeer_Pre_Migration"
    MULE_PRE_WINTER = "MuleDeer_Pre_Winter"
    MULE_POST_SUMMER = "MuleDeer_Post_Summer"
    MULE_POST_MIGRATION = "MuleDeer_Post_Migration"
    MULE_POST_WINTER = "MuleDeer_Post_Winter"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    # Check out Spatial Analyst extension
    hqtlib.CheckOutSpatialAnalyst()

    # Check provided layers
    if not Map_Units_Provided and not Proposed_Modified_Features_Provided:
        arcpy.AddError("ERROR:: Please provide a 'Map_Units' and/or "
                       "'Proposed_Modified_Features' feature.")
        sys.exit(0)

    if not Proposed_Modified_Features_Provided:
        # Ensure Proposed_Modified_Features does not exist
        if arcpy.Exists("Proposed_Modified_Features"):
            arcpy.AddError("ERROR:: A 'Proposed_Modified_Features' layer "
                           "was detected in the project's geodatabase. "
                           "Provide the 'Proposed_Modified_Features' layer "
                           "and re-run Credit Tool 2.")
            sys.exit(0)

    if Map_Units_Provided:
        # Clear selection, if present
        util.ClearSelectedFeatures(Map_Units_Provided)

        # Check provided layer
        feature = Map_Units_Provided
        required_fields = ["Map_Unit_ID", "Map_Unit_Name"]
        no_null_fields = ["Map_Unit_ID"]
        expected_fcs = [CREDIT_PROJECT_AREA]
        hqtlib.CheckPolygonInput(feature, required_fields, expected_fcs,
                                 no_null_fields)

        # Update Map Units layer with provided layer
        provided_input = Map_Units_Provided
        parameter_name = MAP_UNITS
        preserve_existing = False
        Map_Units = util.AdoptParameter(provided_input, parameter_name,
                                          preserve_existing)

        # Add Map Units layer to map
        layerFile = cheStandard.getLayerFile("MapUnits.lyr")
        util.AddToMap(Map_Units, layerFile)

        # Provide location of Credit Project Area
        Credit_Project_Area = CREDIT_PROJECT_AREA

    if Proposed_Modified_Features_Provided:
        # Clear selection, if present
        util.ClearSelectedFeatures(Proposed_Modified_Features_Provided)

        # Check provided layer
        required_fields = ["Type", "Subtype"]
        no_null_fields = required_fields
        expected_fcs = None
        hqtlib.CheckPolygonInput(Proposed_Modified_Features_Provided,
                                 required_fields, expected_fcs, no_null_fields)

        # Update Proposed_Modified_Features with provided layer
        provided_input = Proposed_Modified_Features_Provided
        parameterName = PROPOSED_MODIFIED_FEATURES
        preserve_existing = False
        Proposed_Modified_Features = util.AdoptParameter(
            provided_input, parameterName, preserve_existing
            )

        # Add Proposed Modified Features layer to map
        layerFile = cheStandard.getLayerFile("DebitProjectArea.lyr")
        util.AddToMap(Proposed_Modified_Features, layerFile)

        # Update message
        arcpy.AddMessage("Creating the area of indirect benefit")

        # Create Credit_Project_Area for projects that propose to modify
        # anthropogenic features
        # Create the Indirect_Impact_Area
        in_data = Proposed_Modified_Features
        out_name = INDIRECT_IMPACT_AREA
        Indirect_Impact_Area = hqtlib.CreateIndirectImpactArea(
            in_data, Parameter_Values, out_name
            )

        # Add field "Indirect"
        input_feature = Indirect_Impact_Area
        fieldsToAdd = ["Indirect"]
        fieldTypes = ["TEXT"]
        util.AddFields(input_feature, fieldsToAdd, fieldTypes)

        # Update field 'Indirect' to equal 'True'
        with arcpy.da.UpdateCursor(Indirect_Impact_Area,
                                   fieldsToAdd) as cursor:
            for row in cursor:
                row[0] = "True"
                cursor.updateRow(row)

        if Map_Units_Provided:
            # Merge with Credit_Project_Boundary
            fileList = [Map_Units_Provided, Indirect_Impact_Area]
            out_name = "in_memory/Credit_Project_Boundary"
            Project_Area = arcpy.Union_analysis(fileList, out_name)
        else:
            Project_Area = Indirect_Impact_Area
                
        # Eliminate areas of non-habitat to create Credit_Project_Area
        out_name = CREDIT_PROJECT_AREA
        habitat_bounds = cheStandard.HabitatMgmtArea
        Credit_Project_Area = hqtlib.EliminateNonHabitat(
            Project_Area, out_name, habitat_bounds
            )

    # Detect habitat types impacted directly or indirectly
    is_grsg = cohqt.DetectHabitat(Credit_Project_Area, GrSG_Range)
    is_mule = cohqt.DetectHabitat(Credit_Project_Area, Mule_Range)
    
    # Update message
    arcpy.AddMessage("Dissolving all multi-part map units to create "
                     "Map_Units_Dissolve")

    # Dissolve Map Units
    in_features = MAP_UNITS
    allowable_fields = ["Map_Unit_ID", "Map_Unit_Name", "Indirect"]
    out_name = MAP_UNITS_DISSOLVE
    anthro_features = None
    Map_Units_Dissolve = hqtlib.DissolveMapUnits(in_features, allowable_fields,
                                                 out_name, anthro_features)

    # Update message
    arcpy.AddMessage("Adding Map_Units_Dissolve to map")

    # Add layer to map document
    feature = Map_Units_Dissolve
    layerFile = cheStandard.getLayerFile("MapUnits.lyr")
    util.AddToMap(feature, layerFile, zoom_to=True)

    # Update message
    arcpy.AddMessage("Calculating area in acres for each map unit")

    # Calculate Area
    hqtlib.CalcAcres(Map_Units_Dissolve)

    # Update message
    arcpy.AddMessage("Adding transect field to Map Units Dissolve")

    # Add transects field to map units table
    fields = ["Transects"]
    fieldTypes = ["SHORT"]
    util.AddFields(Map_Units_Dissolve, fields, fieldTypes)

    # Update message
    arcpy.AddMessage("Creating Analysis Area")

    # Create Analysis Area
    out_name = ANALYSIS_AREA
    Analysis_Area = hqtlib.CreateAnalysisArea(Credit_Project_Area,
                                              Parameter_Values,
                                              out_name)

    # Add Analysis_Area to map
    layerFile = cheStandard.getLayerFile("AnalysisArea.lyr")
    util.AddToMap(Analysis_Area, layerFile, zoom_to=True)

    # Set processing extent to Analysis_Area
    arcpy.env.extent = ANALYSIS_AREA

    ### GREATER SAGE-GROUSE ANTHRO DIST & MODIFIERS ###
    if is_grsg:

        # Update message
        arcpy.AddMessage("Calculating proportion of each map unit within 1 km "
                         "of a lek")

        # Calculate proportion of map unit within 1 km of a lek
        inZoneData = Map_Units_Dissolve
        inValueRaster = cheStandard.LekPresenceRaster
        zoneField = "Map_Unit_ID"
        outTable = "Proportion_Lek"
        hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

        # Join the zonal statistic to the Map Units Dissolve table
        field_name = "PropLek"
        hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, field_name)

        # Update message
        arcpy.AddMessage("Calculating proportion of each map unit in the mesic "
                         "precip zone")

        # Calculate Proportion of each map unit in the mesic precip zone
        inZoneData = Map_Units_Dissolve
        inValueRaster = cheStandard.Precip
        zoneField = "Map_Unit_ID"
        outTable = "Proportion_Mesic"
        hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

        # Join the zonal statistic to the Map Units Dissolve table
        field_name = "PropMesic"
        hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, field_name)

        # Update message
        arcpy.AddMessage("Calculating pre-project anthropogenic "
                         "disturbance modifier for greater sage-grouse")

        # Calculate Current_Anthro_Disturbance
        dist_field = "GrSG_Dist"
        weight_field = "GrSG_Weight"
        term = cheStandard.CreditTerms[0]
        unique_proposed_subtypes = []
        anthro_disturbance_type = "Pre"

        Current_Anthro_Disturbance = cohqt.CalcAnthroDisturbance(
            Parameter_Values, term, unique_proposed_subtypes,
            anthro_disturbance_type, cheStandard, dist_field, weight_field,
            cellSize, emptyRaster
        )
        Current_Anthro_Disturbance.save(CURRENT_ANTHRO_DISTURBANCE)

        # Update message
        arcpy.AddMessage("Current_Anthro_Disturbance Calculated")
        arcpy.AddMessage("Calculating Pre-Project Habitat Modifiers for"
                         "Greater Sage-Grouse")

        # Calculate pre-project cumulative habitat modifiers
        winterHabitatPre = cohqt.calcWinterHabitatGRSG(
            Current_Anthro_Disturbance,
            ConiferModifier,
            GrSG_LDI,
            GrSG_Habitat
            )
        LSDMWinterPre = cohqt.applyLekUpliftModifierPre(
            winterHabitatPre,
            LekPresenceRaster
            )
        breedingHabitatPre = cohqt.calcBreedingHabitatGRSG(
            Current_Anthro_Disturbance,
            ConiferModifier,
            GrSG_LDI,
            Lek_Distance_Modifier,
            GrSG_Habitat
            )
        LSDMBreedingPre = cohqt.applyLekUpliftModifierPre(
            breedingHabitatPre,
            LekPresenceRaster
            )
        summerHabitatPre = cohqt.calcSummerHabitatGRSG(
            Current_Anthro_Disturbance,
            ConiferModifier,
            GrSG_LDI,
            SageModifier,
            GrSG_Habitat
            )
        LSDMSummerPre = cohqt.applyLekUpliftModifierPre(
            summerHabitatPre,
            LekPresenceRaster
            )
        seasonalHabitatRasters = [LSDMWinterPre, LSDMBreedingPre, LSDMSummerPre]

        # Save outputs
        # winterHabitatPre.save(GRSG_PRE_WINTER)
        LSDMWinterPre.save(GRSG_PRE_WINTER)
        # breedingHabitatPre.save(GRSG_PRE_BREEDING)
        LSDMBreedingPre.save(GRSG_PRE_BREEDING)
        # summerHabitatPre.save(GRSG_PRE_SUMMER)
        LSDMSummerPre.save(GRSG_PRE_SUMMER)

        # Initialize list of uplift rasters to combine for LekUpliftModifier
        upliftRasters = []
        if arcpy.Exists(CONIFER_TREATMENT_AREA):
            # Calculate post-project conifer modifier
            Conifer_Cover = cheStandard.ConiferCover
            coniferModifierPost = cohqt.calcConiferPost(
                CONIFER_TREATMENT_AREA, Conifer_Cover
            )
            coniferModifierPost.save(POST_CONIFER_MODIFIER)

            # Calculate uplift from conifer removal
            coniferUplift = cohqt.calcUplift(ConiferModifier, coniferModifierPost)
            upliftRasters.append(coniferUplift)

        else:
            coniferModifierPost = ConiferModifier

        if arcpy.Exists(PROPOSED_MODIFIED_FEATURES):
            # Prepare proposed anthropogenic features
            unique_proposed_subtypes = cohqt.convertProposedToRasterCredit(
                PROPOSED_MODIFIED_FEATURES, cellSize
            )

            anthroPath = cheStandard.AnthroFeaturePath
            cohqt.combineProposedWithCurrentCredit(anthroPath, unique_proposed_subtypes)

            # Update message
            arcpy.AddMessage("Calculating post-project anthropogenic "
                             "disturbance modifier for greater sage-grouse")

            # Calculate post-project anthropogenic disturbance
            term = cheStandard.CreditTerms[1]
            anthro_disturbance_type = "Post"

            Projected_Anthro_Disturbance = cohqt.CalcAnthroDisturbance(
                Parameter_Values, term, unique_proposed_subtypes,
                anthro_disturbance_type, cheStandard, dist_field, weight_field,
                cellSize, emptyRaster
            )

            Projected_Anthro_Disturbance.save(PROJECTED_ANTHRO_DISTURBANCE)

            # Update message
            arcpy.AddMessage("Projected_Anthro_Disturbance Calculated")

            # Calculate uplift from anthro feature removal
            anthroUplift = cohqt.calcUplift(Current_Anthro_Disturbance,
                                      Projected_Anthro_Disturbance)
            upliftRasters.append(anthroUplift)

            # Update message
            arcpy.AddMessage("Merging indirect benefits area and map units layer")

            # Combine the Map Units layer and Indirect Impact Layer
            indirect_benefit_area = CREDIT_PROJECT_AREA
            mgmt_map_units = Map_Units_Dissolve
            Map_Units_Dissolve = hqtlib.AddIndirectBenefitArea(indirect_benefit_area,
                                                      mgmt_map_units)

        else:
            Projected_Anthro_Disturbance = Current_Anthro_Disturbance

            # Add Indirect field to Map Units layer and populate with False
            # Add field "Indirect"
            feature = Map_Units_Dissolve
            fieldsToAdd = ["Indirect"]
            fieldTypes = ["TEXT"]
            util.AddFields(feature, fieldsToAdd, fieldTypes)

            # Update field to equal "False"
            with arcpy.da.UpdateCursor(feature,
                                       fieldsToAdd) as cursor:
                for row in cursor:
                    row[0] = "False"
                    cursor.updateRow(row)

        # Calc zonal stats for pre-project modifiers (three seasons)
        term = cheStandard.CreditTerms[0]
        for season, raster in zip(cheStandard.GrSGSeasons, seasonalHabitatRasters):
            # Update message
            arcpy.AddMessage("Summarizing GrSG " + term + " " + season)

            # Calculate zonal statistics for each map unit
            inZoneData = Map_Units_Dissolve
            inValueRaster = raster
            zoneField = "Map_Unit_ID"
            outTable = "GrSG_Stats_" + term + "_" + season
            hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

            # Join the zonal statistic to the Map Units Dissolve table
            field_name = "GrSG_" + term + "_" + season
            hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, field_name)

        if arcpy.Exists("Conifer_Treatment_Area") or \
                arcpy.Exists("Anthro_Features_Removed"):

            # Update message
            arcpy.AddMessage("Calculating Lek Uplift Modifier")

            # Calculate Lek Uplift Modifier
            lekUpliftModifier = cohqt.calcLekUpliftModifier(LekPresenceRaster,
                                                             upliftRasters)
            lekUpliftModifier.save("Lek_Uplift_Modifier")

            # Update message
            arcpy.AddMessage("Calculating Post-Project Habitat Modifiers")

            # Calculate post-project cumulative habtiat modifiers
            winterHabitatPost = cohqt.calcWinterHabitatGRSG(
                Projected_Anthro_Disturbance,
                ConiferModifier,
                GrSG_LDI,
                GrSG_Habitat
                )
            LSDMWinterPost = cohqt.applyLekUpliftModifierPost(
                winterHabitatPost,
                LekPresenceRaster,
                lekUpliftModifier
                )
            breedingHabitatPost = cohqt.calcBreedingHabitatGRSG(
                Projected_Anthro_Disturbance,
                ConiferModifier,
                GrSG_LDI,
                Lek_Distance_Modifier,
                GrSG_Habitat
                )
            LSDMBreedingPost = cohqt.applyLekUpliftModifierPost(
                breedingHabitatPost,
                LekPresenceRaster,
                lekUpliftModifier
                )
            summerHabitatPost = cohqt.calcSummerHabitatGRSG(
                Projected_Anthro_Disturbance,
                ConiferModifier,
                GrSG_LDI,
                SageModifier,
                GrSG_Habitat
                )
            LSDMSummerPost = cohqt.applyLekUpliftModifierPost(
                summerHabitatPost,
                LekPresenceRaster,
                lekUpliftModifier
                )

            seasonalHabitatRasters = [LSDMWinterPost, LSDMBreedingPost, LSDMSummerPost]

            # Save outputs
            # winterHabitatPost.save("Post_Seasonal_Winter")
            LSDMWinterPost.save(GRSG_POST_WINTER)
            # breedingHabitatPost.save("Post_Seasonal_Breeding")
            LSDMBreedingPost.save(GRSG_POST_BREEDING)
            # summerHabitatPost.save("Post_Seasonal_Summer")
            LSDMSummerPost.save(GRSG_POST_SUMMER)

            # Calc zonal stats for post-project modifiers
            term = cheStandard.CreditTerms[1]
            for season, raster in zip(cheStandard.GrSGSeasons, seasonalHabitatRasters):
                # Update message
                arcpy.AddMessage("Summarizing GrSG " + term + " " + season)

                # Calculate zonal statistics for each map unit
                inZoneData = Map_Units_Dissolve
                inValueRaster = raster
                zoneField = "Map_Unit_ID"
                outTable = "GrSG_Stats_" + term + "_" + season
                hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

                # Join the zonal statistic to the Map Units Dissolve table
                field_name = "GrSG_" + term + "_" + season
                hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, field_name)

        # Calculate Credit Intensity

    ### END GREATER SAGE-GROUSE ###

    ### MULE DEER ANTHRO DIST & MODIFIERS ###
    if is_mule:
        # Update message
        arcpy.AddMessage("Calculating pre-project anthropogenic disturbance "
                        "modifier for mule deer - process may repeat for "
                        "habitats in mixed PJ and open habitat")

        # # Calculat pre-project anthropogenic disturbance
        # dist_field = "MDO_Dist"
        # weight_field = "MDO_Weight"
        # term = cheStandard.CreditTerms[0]
        # unique_proposed_subtypes = []
        # anthro_disturbance_type = "Pre"
        #
        # Current_Anthro_Disturbance = hqtlib.cheCalcAnthroDisturbance(
        #     Parameter_Values, term, unique_proposed_subtypes,
        #     anthro_disturbance_type, cheStandard, dist_field, weight_field,
        #     cellSize, emptyRaster
        # )
        # Current_Anthro_Disturbance.save(CURRENT_ANTHRO_DISTURBANCE_MD)

        # Calculate pre-project anthropogenic disturbance
        # Calculate pre-project in PJ
        dist_field = "MDP_Dist"
        weight_field = "MDP_Weight"
        term = cheStandard.CreditTerms[0]
        unique_proposed_subtypes = []
        anthro_disturbance_type = "Pre"

        anthro_pj = cohqt.CalcAnthroDisturbance(
            Parameter_Values, term, unique_proposed_subtypes,
            anthro_disturbance_type, cheStandard, dist_field, weight_field,
            cellSize, emptyRaster
        )
        anthro_pj.save(CURRENT_ANTHRO_DISTURBANCE_MD + "_P")

        # Calculate pre-project in Open
        dist_field = "MDO_Dist"
        weight_field = "MDO_Weight"
        term = cheStandard.CreditTerms[0]
        unique_proposed_subtypes = []
        anthro_disturbance_type = "Pre"

        anthro_open = cohqt.CalcAnthroDisturbance(
            Parameter_Values, term, unique_proposed_subtypes,
            anthro_disturbance_type, cheStandard, dist_field, weight_field,
            cellSize, emptyRaster, mask=BWMD_Open
        )
        anthro_open.save(CURRENT_ANTHRO_DISTURBANCE_MD + "_O")

        # Combine PJ and Open
        # If outside open, make 1
        anthro_open_only = Con(BWMD_Open == 1, anthro_open, 1)
        anthro_open_only.save(CURRENT_ANTHRO_DISTURBANCE_MD + "_OO")

        # Select minimum of pj and open rasters
        Current_Anthro_Disturbance = Con(anthro_open_only < anthro_pj,
                                        anthro_open_only, anthro_pj)
        Current_Anthro_Disturbance.save(CURRENT_ANTHRO_DISTURBANCE_MD)

        # Clean up
        arcpy.Delete_management("temp_masked_raster")
        # arcpy.Delete_management(CURRENT_ANTHRO_DISTURBANCE_MD + "_P")
        # arcpy.Delete_management(CURRENT_ANTHRO_DISTURBANCE_MD + "_O")
        # arcpy.Delete_management(CURRENT_ANTHRO_DISTURBANCE_MD + "_OO")

        # Update message
        arcpy.AddMessage("Calculating Pre-Project Habitat Modifiers")

        # Calculate pre-project cumulative habitat modifiers
        summerHabitatPre = cohqt.calcSummerHabitatMD(
            Current_Anthro_Disturbance, MuleDeer_LDI, SummerModifier,
            SuitableHabitat=None
        )
        # LSDMWinterPre = cohqt.applyLekUpliftModifierPre(summerHabitatPre,
        #                                                  LekPresenceRaster)
        migratoryHabitatPre = cohqt.calcMigratoryHabitatMD(
            Current_Anthro_Disturbance, MuleDeer_LDI, MigrationModifier,
            SuitableHabitat=None
        )
        # LSDMBreedingPre = cohqt.applyLekUpliftModifierPre(migratoryHabitatPre,
        #                                                    LekPresenceRaster)
        winterHabitatPre = cohqt.calcWinterHabitatMD(
            Current_Anthro_Disturbance, MuleDeer_LDI, WinterModifier,
            SuitableHabitat=None
        )
        # LSDMSummerPre = cohqt.applyLekUpliftModifierPre(winterHabitatPre,
        #                                                  LekPresenceRaster)
        seasonalHabitatRasters = [summerHabitatPre, migratoryHabitatPre, winterHabitatPre]

        # Save outputs
        summerHabitatPre.save(MULE_PRE_SUMMER)
        # LSDMWinterPre.save("Pre_LSDM_Winter")
        migratoryHabitatPre.save(MULE_PRE_MIGRATION)
        # LSDMBreedingPre.save("Pre_LSDM_Breeding")
        winterHabitatPre.save(MULE_PRE_WINTER)
        # LSDMSummerPre.save("Pre_LSDM_Summer")

        # Update message
        arcpy.AddMessage("Current_Anthro_Disturbance Calculated")

        # Calc zonal stats for pre-project modifiers (three seasons)
        term = cheStandard.DebitTerms[0]
        for season, raster in zip(cheStandard.MuleDeerSeasons, seasonalHabitatRasters):
            # Update message
            arcpy.AddMessage("Summarizing Mule Deer " + term + " " + season)

            # Calculate zonal statistics for each map unit
            inZoneData = Map_Units_Dissolve
            inValueRaster = raster
            zoneField = "Map_Unit_ID"
            outTable = "Mule_Stats_" + term + "_" + season
            hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

            # Join the zonal statistic to the Map Units Dissolve table
            field_name = "Mule_" + term + "_" + season
            hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, field_name)

        # # Calculate average of three seasonal habitat rasters pre-project
        # finalPreCumulative = hqtlib.calcAverageHabitatQuality(
        #     seasonalHabitatRasters
        # )
        # finalPreCumulative.save(CUMULATIVE_MODIFIER_PRE)

        if arcpy.Exists(PROPOSED_MODIFIED_FEATURES):
            # Update message
            arcpy.AddMessage("Calculating post-project anthropogenic "
                            "disturbance modifier")

            # Calculate post-project anthropogenic disturbance
            term = cheStandard.CreditTerms[1]
            anthro_disturbance_type = "Post"

            Projected_Anthro_Disturbance = cohqt.CalcAnthroDisturbance(
                Parameter_Values, term, unique_proposed_subtypes,
                anthro_disturbance_type, cheStandard, dist_field, weight_field,
                cellSize, emptyRaster
            )

            Projected_Anthro_Disturbance.save(PROJECTED_ANTHRO_DISTURBANCE_MD)

            # Update message
            arcpy.AddMessage("Projected_Anthro_Disturbance Calculated")

            # Calculate post-project cumulative habitat modifiers
            summerHabitatPost = cohqt.calcSummerHabitatMD(
                Projected_Anthro_Disturbance, MuleDeer_LDI, SummerModifier,
                SuitableHabitat=None
            )
            # LSDMWinterPost = cohqt.applyLekUpliftModifierPost(summerHabitatPost,
            #                                                  LekPresenceRaster)
            migratoryHabitatPost = cohqt.calcMigratoryHabitatMD(
                Projected_Anthro_Disturbance, MuleDeer_LDI, MigrationModifier,
                SuitableHabitat=None
            )
            # LSDMBreedingPost = cohqt.applyLekUpliftModifierPost(migratoryHabitatPost,
            #                                                    LekPresenceRaster)
            winterHabitatPost = cohqt.calcWinterHabitatMD(
                Projected_Anthro_Disturbance, MuleDeer_LDI, WinterModifier,
                SuitableHabitat=None
            )
            # LSDMSummerPost = cohqt.applyLekUpliftModifierPost(winterHabitatPost,
            #                                                  LekPresenceRaster)
            seasonalHabitatRasters = [summerHabitatPost, migratoryHabitatPost,
                                    winterHabitatPost]

            # Save outputs
            summerHabitatPost.save(MULE_POST_SUMMER)
            # LSDMWinterPre.save("Pre_LSDM_Winter")
            migratoryHabitatPost.save(MULE_POST_MIGRATION)
            # LSDMBreedingPre.save("Pre_LSDM_Breeding")
            winterHabitatPost.save(MULE_POST_WINTER)
            # LSDMSummerPre.save("Pre_LSDM_Summer")

            # Calc zonal stats for pre-project modifiers (three seasons)
            term = cheStandard.DebitTerms[1]
            for season, raster in zip(cheStandard.MuleDeerSeasons, seasonalHabitatRasters):
                # Update message
                arcpy.AddMessage("Summarizing Mule Deer " + term + season)

                # Calculate zonal statistics for each map unit
                inZoneData = Map_Units_Dissolve
                inValueRaster = raster
                zoneField = "Map_Unit_ID"
                outTable = "Mule_Stats_" + term + season
                hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

                # Join the zonal statistic to the Map Units Dissolve table
                field_name = "Mule_" + term + "_" + season
                hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, field_name)

            # # Calculate average of three seasonal habitat rasters post-project
            # finalPostCumulative = hqtlib.calcAverageHabitatQuality(
            #     seasonalHabitatRasters
            # )
            # finalPostCumulative.save(CUMULATIVE_MODIFIER_POST)

            # Calculate permanent cumulative habtiat modifiers

            # Update message
            arcpy.AddMessage("Calculating Mule Deer Benefit")

            # Calculate impact
            pre_fields = ["Mule_Pre_Summer", "Mule_Pre_Migration", "Mule_Pre_Winter"]
            post_fields = ["Mule_Post_Summer", "Mule_Post_Migration", "Mule_Post_Winter"]
            out_fields = ["Mule_Summer_Benefit", "Mule_Migration_Benefit", "Mule_Winter_Benefit"]
            for i in range(len(pre_fields)):
                pre_field = pre_fields[i]
                post_field = post_fields[i]
                out_field = out_fields[i]
                cohqt.calcDebits(Map_Units_Dissolve, pre_field, post_field, out_field)

        # # Export data to Excel
        input_Tables = [MAP_UNITS_DISSOLVE]
        for table in input_Tables:
             hqtlib.ExportToExcel(table, Project_Folder, Project_Name)

    ### END MULE DEER ###
    if not is_grsg and not is_mule:
        arcpy.AddMessage("Impacts were not detected in any habitat type. "
                         "Please check credit project boundary and try "
                         "again")
    # Clean up
    for raster in arcpy.ListRasters("*_Subtype_Disturbance"):
        arcpy.Delete_management(raster)

    for raster in arcpy.ListRasters("*_Type_Disturbance"):
        arcpy.Delete_management(raster)

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
