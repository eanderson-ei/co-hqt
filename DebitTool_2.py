"""
Name:     DebitTool_2.py
Author:   Erik Anderson
Created:  December 18, 2018
Revised:  February 25, 2019
Version:  Created using Python 3.6.3, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better,
          Spatial Analyst extension

Path to the project's workspace is derived from the Proposed_Surface_Disturbance
feature class provided by the user.

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
    Proposed_Surface_Disturbance_Provided = arcpy.GetParameterAsText(0)
    Proposed_Modified_Features_Provided = arcpy.GetParameterAsText(1)  # optional

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    arcpy.AddMessage("Python version: " + sys.version)
    # Construct pathname to workspace
    projectGDB = arcpy.Describe(Proposed_Surface_Disturbance_Provided).path
    arcpy.AddMessage("Project geodatabase: " + projectGDB)

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
        arcpy.CreateFolder_management(arcpy.Describe(projectGDB).path, 'scratch')
    arcpy.env.scratchWorkspace = scratch_folder
    # Overwrite outputs
    arcpy.env.overwriteOutput = True

    # DEFINE GLOBAL VARIABLES
    Parameter_Values = cheStandard.ParameterValues
    habitat_bounds = cheStandard.HabitatMgmtArea
    ConiferModifier = cheStandard.ConiferModifier
    GrSG_LDI = cheStandard.GrSG_LDI
    LekPresenceRaster = cheStandard.LekPresenceRaster
    Lek_Distance_Modifier = cheStandard.LekDistanceModifier
    SageModifier = cheStandard.SageModifier
    GrSGHabitat = cheStandard.BWSGHab
    MuleDeerHabitat = cheStandard.BWMDHab
    emptyRaster = cheStandard.EmptyRaster
    MigrationModifier = cheStandard.MuleDeerMigrationMod
    WinterModifier = cheStandard.MuleDeerWinterMod
    SummerModifier = cheStandard.MuleDeerSummerMod
    MuleDeer_LDI = cheStandard.MuleDeerLDI
    BWMD_Open = cheStandard.BWMD_Open
    GrSG_Range = cheStandard.GrSGHabitat
    Mule_Range = cheStandard.MuleDeerHabitat
    cellSize = arcpy.GetRasterProperties_management(
        emptyRaster, "CELLSIZEX").getOutput(0)

    # Filenames for feature classes or rasters used by this script
    PROPOSED_SURFACE_DISTURBANCE_DEBITS = "Proposed_Surface_Disturbance_Debits"

    # Filenames for feature classes or rasters created by this script
    ANALYSIS_AREA = "Analysis_Area"
    DEBIT_PROJECT_AREA = "Debit_Project_Area"
    INDIRECT_IMPACT_AREA = "Indirect_Impact_Area"
    INDIRECT_BENEFIT_AREA = "Indirect_Benefit_Area"
    PROPOSED_MODIFIED_FEATURES = "Proposed_Modified_Features"
    DEBIT_PROJECT_IMPACT = "GrSG_Impact"
    MAP_UNITS = "Map_Units"
    # GrSG Filenames
    LEK_DISTURBANCE_MODIFIER = "Lek_Disturbance_Modifier"
    CUMULATIVE_MODIFIER_PRE = "GRSG_Pre_Cumulative_Modifier"
    CUMULATIVE_MODIFIER_POST = "GRSG_Post_Cumulative_Modifier"
    CURRENT_ANTHRO_DISTURBANCE = "GRSG_Pre_Anthro_Disturbance"
    PROJECTED_ANTHRO_DISTURBANCE = "GRSG_Post_Anthro_Disturbance"
    GRSG_PRE_BREEDING = "GRSG_Pre_Breeding"
    GRSG_PRE_SUMMER = "GRSG_Pre_Summer"
    GRSG_PRE_WINTER = "GRSG_Pre_Winter"
    GRSG_POST_BREEDING = "GRSG_Post_Breeding"
    GRSG_POST_SUMMER = "GRSG_Post_Summer"
    GRSG_POST_WINTER = "GRSG_Post_Winter"
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

    if not Proposed_Modified_Features_Provided:
        # Ensure Proposed_Modified_Features does not exist
        if arcpy.Exists("Proposed_Modified_Features"):
            arcpy.AddError("ERROR:: A 'Proposed_Modified_Features' layer "
                           "was detected in the project's geodatabase. "
                           "Provide the 'Proposed_Modified_Features' layer "
                           "and re-run Debit Tool 2.")
            sys.exit(0)

    # Clear selection, if present
    util.ClearSelectedFeatures(Proposed_Surface_Disturbance_Provided)

    # Check Proposed_Surface_Disturbance
    feature = Proposed_Surface_Disturbance_Provided
    required_fields = ["Type", "Subtype", "Surface_Disturbance"]
    no_null_fields = required_fields
    expected_fcs = None
    hqtlib.CheckPolygonInput(feature, required_fields,
                            expected_fcs, no_null_fields)

    # Update Proposed_Surface_Disturbance layer with provided layer
    provided_input = Proposed_Surface_Disturbance_Provided
    parameter_name = PROPOSED_SURFACE_DISTURBANCE_DEBITS
    Proposed_Surface_Disturbance = util.AdoptParameter(
        provided_input, parameter_name, preserve_existing=False
        )

    # Replace Proposed_Surface_Disturbance_Debits layer on map
    layerFile = cheStandard.getLayerFile("ProposedSurfaceDisturbance.lyr")
    util.AddToMap(Proposed_Surface_Disturbance, layerFile)

    # Add field for Disturbance_Type and populate. Values will be used in
    # Map_Units_Dissolve to identify map units of direct disturbance
    feature = Proposed_Surface_Disturbance
    fields = ["Disturbance_Type"]
    fieldTypes = ["TEXT"]
    util.AddFields(feature, fields, fieldTypes)

    with arcpy.da.UpdateCursor(feature, ["Surface_Disturbance"] + fields) as cursor:
        for row in cursor:
            row[1] = "Direct_" + row[0]
            cursor.updateRow(row)

    # Update message
    arcpy.AddMessage("Creating the area of indirect impact")

    # Buffer proposed surface disturbance to create Indirect_Impact_Area
    in_data = Proposed_Surface_Disturbance
    out_name = INDIRECT_IMPACT_AREA
    Indirect_Impact_Area = hqtlib.CreateIndirectImpactArea(
        in_data, Parameter_Values, out_name
        )

    # Set up flag for projects that propose to modify anthro features
    includes_anthro_mod = False

    if Proposed_Modified_Features_Provided:
        # Update flag
        includes_anthro_mod = True

        # Clear selection, if present
        util.ClearSelectedFeatures(Proposed_Modified_Features_Provided)

        # Check provided layer
        required_fields = ["Type", "Subtype"]
        no_null_fields = required_fields
        expected_fcs = None
        hqtlib.CheckPolygonInput(Proposed_Modified_Features_Provided, required_fields,
                                expected_fcs, no_null_fields)

        # Update Proposed_Modified_Features with provided layer and add to map
        provided_input = Proposed_Modified_Features_Provided
        parameterName = PROPOSED_MODIFIED_FEATURES
        preserve_existing = False
        Proposed_Modified_Features = util.AdoptParameter(
            provided_input, parameterName, preserve_existing
        )

        # Add Proposed Modified Features layer to map
        layerFile = cheStandard.getLayerFile("ProposedSurfaceDisturbance.lyr")
        util.AddToMap(Proposed_Modified_Features, layerFile)

        # Update message
        arcpy.AddMessage("Creating the area of indirect benefit")

        # Create the Indirect_Impact_Area
        in_data = Proposed_Modified_Features
        out_name = INDIRECT_BENEFIT_AREA
        Indirect_Benefit_Area = hqtlib.CreateIndirectImpactArea(
            in_data, Parameter_Values, out_name
            )

        # Union the indirect benefit area and the indirect impact area
        in_features = [Indirect_Impact_Area, Indirect_Benefit_Area]
        out_name = "in_memory/Impact_Union"
        Impact_Union = arcpy.Union_analysis(in_features, out_name)

        # Dissolve the unioned indirect impact and benefit areas as
        # Indirect Impact Area
        in_features = Impact_Union
        out_feature_class = INDIRECT_IMPACT_AREA
        Indirect_Impact_Area = arcpy.Dissolve_management(in_features,
                                                         out_feature_class)

    # Detect habitat types impacted directly or indirectly
    is_grsg = cohqt.DetectHabitat(Indirect_Impact_Area, GrSG_Range)
    is_mule = cohqt.DetectHabitat(Indirect_Impact_Area, Mule_Range)
    
    # Update message
    arcpy.AddMessage("Determining project area - eliminating areas of non-"
                     "habitat from the Project Area")

    # Eliminate non-habitat
    project_area = Indirect_Impact_Area
    out_name = DEBIT_PROJECT_AREA
    Debit_Project_Area = hqtlib.EliminateNonHabitat(
        project_area, out_name, habitat_bounds
        )

    # Calculate Area
    hqtlib.CalcAcres(Debit_Project_Area)

    # Add Debit Project Area to map
    feature = Debit_Project_Area
    layerFile = cheStandard.getLayerFile("DebitProjectArea.lyr")
    util.AddToMap(feature, layerFile, zoom_to=True)

    # Update message
    arcpy.AddMessage("Creating Analysis Area")

    # Create Analysis_Area
    out_name = ANALYSIS_AREA
    Analysis_Area = hqtlib.CreateAnalysisArea(Debit_Project_Area,
                                             Parameter_Values,
                                             out_name)

    # Add Analysis_Area to map
    layerFile = cheStandard.getLayerFile("AnalysisArea.lyr")
    util.AddToMap(Analysis_Area, layerFile, zoom_to=True)

    # Set processing extent to Analysis_Area
    arcpy.env.extent = ANALYSIS_AREA

    # Prepare proposed anthropogenic features
    unique_proposed_subtypes = cohqt.convertProposedToRasterDebit(
        Proposed_Surface_Disturbance, cellSize
        )

    anthroPath = cheStandard.AnthroFeaturePath
    cohqt.combineProposedWithCurrentDebit(anthroPath, unique_proposed_subtypes)

    # # Do something about anthropogenic mod features
    # if includes_anthro_mod:
    #     unique_proposed_subtypes_removed = hqtlib.convertProposedToRaster(
    #         Proposed_Modified_Features, cellSize
    #       )
    #
    #     anthroPath = cheStandard.AnthroFeaturePath
    #     hqtlib.combineProposedWithCurrent(anthroPath, unique_proposed_subtypes)

    ### GREATER SAGE-GROUSE ANTHRO DIST & MODIFIERS ###
    if is_grsg:
        # Update message
        arcpy.AddMessage("Calculating pre-project anthropogenic disturbance "
                         "modifier for greater sage-grouse")

        # Calculate pre-project anthropogenic disturbance
        dist_field = "GrSG_Dist"
        weight_field = "GrSG_Weight"
        term = cheStandard.DebitTerms[0]
        anthro_disturbance_type = "Pre"

        Current_Anthro_Disturbance = cohqt.CalcAnthroDisturbance(
            Parameter_Values, term, unique_proposed_subtypes,
            anthro_disturbance_type, cheStandard, dist_field, weight_field,
            cellSize, emptyRaster
            )
        Current_Anthro_Disturbance.save(CURRENT_ANTHRO_DISTURBANCE)

        # Update message
        arcpy.AddMessage("Current_Anthro_Disturbance Calculated")
        arcpy.AddMessage("Calculating post-project anthropogenic "
                         "disturbance modifier for greater sage-grouse")

        # Calculate post-project anthropogenic disturbance
        term = cheStandard.DebitTerms[1]
        anthro_disturbance_type = "Post"

        Projected_Anthro_Disturbance = cohqt.CalcAnthroDisturbance(
            Parameter_Values, term, unique_proposed_subtypes,
            anthro_disturbance_type, cheStandard, dist_field, weight_field,
            cellSize, emptyRaster
            )

        Projected_Anthro_Disturbance.save(PROJECTED_ANTHRO_DISTURBANCE)

        # Update message
        arcpy.AddMessage("Projected_Anthro_Disturbance Calculated")
        arcpy.AddMessage("Calculating lek disturbance modifier")

        # Calculate permanent anthropogenic disturbance

        # Calculate Lek Disturbance Modifier
        term = cheStandard.DebitTerms[1]
        anthro_disturbance_type = "LekDisturbanceModifier"

        Lek_Disturbance_Modifier = cohqt.CalcAnthroDisturbance(
            Parameter_Values, term, unique_proposed_subtypes,
            anthro_disturbance_type, cheStandard, dist_field, weight_field,
            cellSize, emptyRaster
            )

        Lek_Disturbance_Modifier.save(LEK_DISTURBANCE_MODIFIER)

        # Update message
        arcpy.AddMessage("Calculating Pre-Project Habitat Modifiers")

        # Calculate pre-project cumulative habitat modifiers
        winterHabitatPre = cohqt.calcWinterHabitatGRSG(
            Current_Anthro_Disturbance,
            ConiferModifier,
            GrSG_LDI,
            GrSGHabitat
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
            GrSGHabitat
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
            GrSGHabitat
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

        # Calculate average of three seasonal habitat rasters pre-project
        finalPreCumulative = cohqt.calcAverageHabitatQuality(
            seasonalHabitatRasters
        )
        finalPreCumulative.save(CUMULATIVE_MODIFIER_PRE)

        # Calculate post-project cumulative habtiat modifiers
        winterHabitatPost = cohqt.calcWinterHabitatGRSG(
            Projected_Anthro_Disturbance,
            ConiferModifier,
            GrSG_LDI,
            GrSGHabitat
            )
        LSDMWinterPost = cohqt.applyLekUpliftModifierPost(
            winterHabitatPost,
            LekPresenceRaster,
            Lek_Disturbance_Modifier
            )
        breedingHabitatPost = cohqt.calcBreedingHabitatGRSG(
            Projected_Anthro_Disturbance,
            ConiferModifier,
            GrSG_LDI,
            Lek_Distance_Modifier,
            GrSGHabitat
            )
        LSDMBreedingPost = cohqt.applyLekUpliftModifierPost(
            breedingHabitatPost,
            LekPresenceRaster,
            Lek_Disturbance_Modifier
            )
        summerHabitatPost = cohqt.calcSummerHabitatGRSG(
            Projected_Anthro_Disturbance,
            ConiferModifier,
            GrSG_LDI,
            SageModifier,
            GrSGHabitat
            )
        LSDMSummerPost = cohqt.applyLekUpliftModifierPost(
            summerHabitatPost,
            LekPresenceRaster,
            Lek_Disturbance_Modifier
            )

        seasonalHabitatRasters = [LSDMWinterPost, LSDMBreedingPost, LSDMSummerPost]

        # Save outputs
        # winterHabitatPost.save("Post_Seasonal_Winter")
        LSDMWinterPost.save(GRSG_POST_WINTER)
        # breedingHabitatPost.save("Post_Seasonal_Breeding")
        LSDMBreedingPost.save(GRSG_POST_BREEDING)
        # summerHabitatPost.save("Post_Seasonal_Summer")
        LSDMSummerPost.save(GRSG_POST_SUMMER)

        # Calculate average of three seasonal habitat rasters post-project
        finalPostCumulative = cohqt.calcAverageHabitatQuality(
            seasonalHabitatRasters
        )
        finalPostCumulative.save(CUMULATIVE_MODIFIER_POST)

        # Calculate permanent cumulative habtiat modifiers

        # Calculate Zonal Statistics for cumulative modifier rasters
        # Add field to use for zonal statistics
        inTable = Debit_Project_Area
        fields = ["ZONAL"]
        field_types = ["SHORT"]
        util.AddFields(inTable, fields, field_types)

        # Populate field with value 1
        arcpy.CalculateField_management(inTable, fields[0], 1, "PYTHON_9.3", "")

        # Update message
        arcpy.AddMessage("Calculating debits for greater sage-grouse")

        # Calculate zonal statistics for pre-project
        inZoneData = Debit_Project_Area
        inValueRaster = finalPreCumulative
        zoneField = fields[0]
        outTable = "GRSG_Stats_Pre"
        hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

        # Join the zonal statistic to the Debit Project Area table
        fieldName = "GRSG_Pre_Project"
        hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

        # Calculate zonal statistics for post-project
        inZoneData = Debit_Project_Area
        inValueRaster = finalPostCumulative
        zoneField = fields[0]
        outTable = "GRSG_Stats_Post"
        hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

        # Join the zonal statistic to the Debit Project Area table
        fieldName = "GrSG_Post_Project"
        hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

        # Calculate debits (if not collecting field data)
        cohqt.calcDebits(Debit_Project_Area, "GRSG_Pre_Project",
                          "GrSG_Post_Project", "Debits")

        # Update message
        arcpy.AddMessage("Creating visualization of impact from debit project")

        # Calculate impact intensity for debit project
        debit_impact = cohqt.calcImpact(finalPreCumulative, finalPostCumulative)
        debit_impact.save(DEBIT_PROJECT_IMPACT)

        # Add Debit Impact raster to map and save map document
        feature = debit_impact
        layerFile = cheStandard.getLayerFile("DebitProjectImpact.lyr")
        util.AddToMap(feature, layerFile, zoom_to=True)

    ### END GREATER SAGE-GROUSE ###

    ### MULE DEER ANTHRO DIST & MODIFIERS ###
    if not is_grsg:
        # Calculate Zonal Statistics for cumulative modifier rasters
        # Add field to use for zonal statistics
        inTable = Debit_Project_Area
        fields = ["ZONAL"]
        field_types = ["SHORT"]
        util.AddFields(inTable, fields, field_types)

        # Populate field with value 1
        arcpy.CalculateField_management(inTable, fields[0], 1, "PYTHON_9.3", "")

    # Update message
    if is_mule:
        arcpy.AddMessage("Calculating pre-project anthropogenic disturbance "
                        "modifier for mule deer")

        # Calculate pre-project anthropogenic disturbance
        # Calculate pre-project in PJ
        dist_field = "MDP_Dist"
        weight_field = "MDP_Weight"
        term = cheStandard.DebitTerms[0]
        #unique_proposed_subtypes = []
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
        term = cheStandard.DebitTerms[0]
    #unique_proposed_subtypes = []
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
        arcpy.AddMessage("Current_Anthro_Disturbance Calculated")
        arcpy.AddMessage("Calculating post-project anthropogenic "
                        "disturbance modifier")

        # Calculate post-project anthropogenic disturbance
        # Calculate post-project in PJ
        dist_field = "MDP_Dist"
        weight_field = "MDP_Weight"
        term = cheStandard.DebitTerms[1]
        #unique_proposed_subtypes = []
        anthro_disturbance_type = "Post"

        anthro_pj = cohqt.CalcAnthroDisturbance(
            Parameter_Values, term, unique_proposed_subtypes,
            anthro_disturbance_type, cheStandard, dist_field, weight_field,
            cellSize, emptyRaster
        )
        anthro_pj.save(PROJECTED_ANTHRO_DISTURBANCE_MD + "_P")

        # Calculate pre-project in Open
        dist_field = "MDO_Dist"
        weight_field = "MDO_Weight"
        term = cheStandard.DebitTerms[1]
        #unique_proposed_subtypes = []
        anthro_disturbance_type = "Post"

        anthro_open = cohqt.CalcAnthroDisturbance(
            Parameter_Values, term, unique_proposed_subtypes,
            anthro_disturbance_type, cheStandard, dist_field, weight_field,
            cellSize, emptyRaster, mask=BWMD_Open
        )
        anthro_open.save(PROJECTED_ANTHRO_DISTURBANCE_MD + "_O")

        # Combine PJ and Open
        # If outside open, make 1
        anthro_open_only = Con(BWMD_Open == 1, anthro_open, 1)
        anthro_open_only.save(PROJECTED_ANTHRO_DISTURBANCE_MD + "_OO")

        # Select minimum of pj and open rasters
        Projected_Anthro_Disturbance = Con(anthro_open_only < anthro_pj,
                                        anthro_open_only, anthro_pj)
        Projected_Anthro_Disturbance.save(PROJECTED_ANTHRO_DISTURBANCE_MD)

        # Update message
        arcpy.AddMessage("Projected_Anthro_Disturbance Calculated")
        # arcpy.AddMessage("Calculating lek disturbance modifier")
        #
        # # Calculate permanent anthropogenic disturbance
        #
        # # Calculate Lek Disturbance Modifier
        # term = cheStandard.CreditTerms[1]
        # anthro_disturbance_type = "LekDisturbanceModifier"
        #
        # Lek_Disturbance_Modifier = hqtlib.cheCalcAnthroDisturbance(
        #     Parameter_Values, term, unique_proposed_subtypes,
        #     anthro_disturbance_type, cheStandard, dist_field, weight_field,
        #     cellSize, emptyRaster
        # )
        #
        # Lek_Disturbance_Modifier.save(LEK_DISTURBANCE_MODIFIER)

        # Update message
        arcpy.AddMessage("Calculating Pre-Project Habitat Modifiers")

        # Calculate pre-project cumulative habitat modifiers
        summerHabitatPre = cohqt.calcSummerHabitatMD(
            Current_Anthro_Disturbance, MuleDeer_LDI, SummerModifier,
            SuitableHabitat=MuleDeerHabitat
        )
        # LSDMWinterPre = cohqt.applyLekUpliftModifierPre(summerHabitatPre,
        #                                                  LekPresenceRaster)
        migratoryHabitatPre = cohqt.calcMigratoryHabitatMD(
            Current_Anthro_Disturbance, MuleDeer_LDI, MigrationModifier,
            SuitableHabitat=MuleDeerHabitat
        )
        # LSDMBreedingPre = cohqt.applyLekUpliftModifierPre(migratoryHabitatPre,
        #                                                    LekPresenceRaster)
        winterHabitatPre = cohqt.calcWinterHabitatMD(
            Current_Anthro_Disturbance, MuleDeer_LDI, WinterModifier,
            SuitableHabitat=MuleDeerHabitat
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

        # Calc zonal stats for pre-project modifiers (three seasons)
        term = cheStandard.DebitTerms[0]
        for season, raster in zip(cheStandard.MuleDeerSeasons, seasonalHabitatRasters):
            # Update message
            arcpy.AddMessage("Summarizing Mule Deer " + term + " " + season)

            # Calculate zonal statistics for each map unit
            inZoneData = Debit_Project_Area
            inValueRaster = raster
            zoneField = fields[0]
            outTable = "Mule_Stats_" + term + "_" + season
            hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

            # Join the zonal statistic to the Map Units Dissolve table
            fieldName = "Mule_" + term + "_" + season
            hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

        # # Calculate average of three seasonal habitat rasters pre-project
        # finalPreCumulative = hqtlib.calcAverageHabitatQuality(
        #     seasonalHabitatRasters
        # )
        # finalPreCumulative.save(CUMULATIVE_MODIFIER_PRE)

        # Calculate post-project cumulative habitat modifiers
        summerHabitatPost = cohqt.calcSummerHabitatMD(
            Projected_Anthro_Disturbance, MuleDeer_LDI, SummerModifier,
            SuitableHabitat=MuleDeerHabitat
        )
        # LSDMWinterPost = cohqt.applyLekUpliftModifierPost(summerHabitatPost,
        #                                                  LekPresenceRaster)
        migratoryHabitatPost = cohqt.calcMigratoryHabitatMD(
            Projected_Anthro_Disturbance, MuleDeer_LDI, MigrationModifier,
            SuitableHabitat=MuleDeerHabitat
        )
        # LSDMBreedingPost = cohqt.applyLekUpliftModifierPost(migratoryHabitatPost,
        #                                                    LekPresenceRaster)
        winterHabitatPost = cohqt.calcWinterHabitatMD(
            Projected_Anthro_Disturbance, MuleDeer_LDI, WinterModifier,
            SuitableHabitat=MuleDeerHabitat
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
            arcpy.AddMessage("Summarizing Mule Deer " + term + " " + season)

            # Calculate zonal statistics for each map unit
            inZoneData = Debit_Project_Area
            inValueRaster = raster
            zoneField = fields[0]
            outTable = "Mule_Stats_" + term + "_" + season
            hqtlib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

            # Join the zonal statistic to the Map Units Dissolve table
            fieldName = "Mule_" + term + "_" + season
            hqtlib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

        # # Calculate average of three seasonal habitat rasters post-project
        # finalPostCumulative = hqtlib.calcAverageHabitatQuality(
        #     seasonalHabitatRasters
        # )
        # finalPostCumulative.save(CUMULATIVE_MODIFIER_POST)

        # Calculate permanent cumulative habtiat modifiers

        # Update message
        arcpy.AddMessage("Calculating Mule Deer Impact")

        # Calculate impact
        pre_fields = ["Mule_Pre_Summer", "Mule_Pre_Migration", "Mule_Pre_Winter"]
        post_fields = ["Mule_Post_Summer", "Mule_Post_Migration", "Mule_Post_Winter"]
        out_fields = ["Mule_Summer_Impact", "Mule_Migration_Impact", "Mule_Winter_Impact"]
        for i in range(len(pre_fields)):
            pre_field = pre_fields[i]
            post_field = post_fields[i]
            out_field = out_fields[i]
            cohqt.calcDebits(Debit_Project_Area, pre_field, post_field, out_field)

        # # Update message
        # arcpy.AddMessage("Creating visualization of impact from debit project")
        #
        # # Calculate impact intensity for debit project
        # debit_impact = hqtlib.calcImpact(finalPreCumulative, finalPostCumulative)
        # debit_impact.save(DEBIT_PROJECT_IMPACT)
        #
        # # Add Debit Impact raster to map and save map document
        # feature = debit_impact
        # layerFile = cheStandard.getLayerFile("DebitProjectImpact.lyr")
        # hqtlib.AddToMap(feature, layerFile, zoom_to=True)

        ### END MULE DEER ###

    if not is_grsg and not is_mule:
        arcpy.AddMessage("Impacts were not detected in any habitat type. "
                         "Please check credit project boundary and try "
                         "again")
    
    # Create Map_Units layer
    in_data = Debit_Project_Area
    out_data = MAP_UNITS
    Map_Units = hqtlib.CreateMapUnits(in_data, out_data)

    # Add Map_Units to map
    layerFile = cheStandard.getLayerFile("MapUnits.lyr")
    util.AddToMap(Map_Units, layerFile)

    # Add fields Map_Unit_ID, Map_Unit_Name, and Meadow to Map_Units
    fields = ["Map_Unit_ID", "Map_Unit_Name", "Notes", "Precip", 
                "Transects"]
    fieldTypes = ["SHORT", "TEXT", "TEXT", "TEXT", "SHORT"]
    util.AddFields(Map_Units, fields, fieldTypes, copy_existing=True)

    # Add Domains to Map_Units layer
    # Create Domain for Map_Unit_ID attributes
    domainName = "Map_Unit_ID"
    range_low = 0
    range_high = 10000
    util.AddRangeDomain(Map_Units, projectGDB,
                        domainName, range_low, range_high)
        
    # Create Domain for Precip attributes
    feature_list = [Map_Units]
    domain_name = "Precip"
    code_list = ["Arid", "Mesic"]
    util.AddCodedTextDomain(feature_list, projectGDB, domain_name,
                            code_list)   
        
    # Update message
    arcpy.AddMessage("Cleaning up workspace")

    # Clean up
    for raster in arcpy.ListRasters("*_Subtype_Disturbance"):
        arcpy.Delete_management(raster)

    for raster in arcpy.ListRasters("*_Type_Disturbance"):
        arcpy.Delete_management(raster)

    arcpy.Delete_management("in_memory")
    try:
        arcpy.Delete_management(scratch_folder)
    except:
        pass

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
