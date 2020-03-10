"""
Name:     cohqt.py
Author:   Erik Anderson
Created:  April 25, 2019
Revised:  April 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better
          Spatial Analyst extension

This library contains modules required to run the Colorado Habitat Exchange,
HQT.

"""

import arcpy
import os
import numpy as np
import util
from arcpy.sa import (Raster, Con, IsNull, EucDistance, Exp, 
CellStatistics, NbrCircle, FocalStatistics, RemapRange, Reclassify,
Float, SetNull)

# ----------------------------------------------------------------------------

# CLASSES

class cheStandard:

    # Filenames and data directories
    _data_folder = "ToolData"
    _input_data = "InputData.gdb"
    _anthro_data = "AnthroData.gdb"
    _layer_files = "LayerFiles"
    _parameter_table = "ParameterValues"
    _grsg_ag_index = "GrSG_Ag_Index"
    _grsg_bw = "GrSG_BW"
    _conifer_cover = "Conifer_Cover"
    _grsg_conifer_modifier = "GrSG_Conifer_Modifier"
    _extent_raster = "Extent_Raster"
    _grsg_habitat_raster = "GrSG_Habitat"
    _grsg_habitat_mgmt_area = "GrSG_Range"
    _lakes = "Lakes"
    _grsg_ldi = "GrSG_LDI"
    _lek_distance_modifier = "GrSG_Lek_Distance_Modifier"
    _lek_presence_raster = "GrSG_LekRaster"
    _mule_deer_habitat_mgmt_area = "Mule_Deer_Range"
    _coordinate_reference = "Program_Scope"
    _mule_deer_mig_mod = "Mule_Deer_Transition_Modifier" #new migration layer
    _mule_deer_summer_mod = "Mule_Deer_Summer_Modifier"
    _mule_deer_winter_mod = "Mule_Deer_Winter_Modifier"
    _mule_deer_ldi = "Mule_Deer_LDI"
    _mule_deer_bw = "Mule_Deer_BW"
    _precip = "Precip"
    _program_scope = "Program_Scope"
    _grsg_sage_modifier = "GrSG_Sage_Modifier"
    _mule_deer_open = "Mule_Deer_Open_Habitat"
    # _urban_index = "Urban_Index"

    # Standard values
    _credit_terms = ["Pre", "Post"]
    _debit_terms = ["Pre", "Post"]
    _grsg_seasons = ["Winter", "Breed", "Summer"]
    _mule_deer_seasons = ["Summer", "Migration", "Winter"]

    def __init__(self, workspace, scriptPath):
        self.workspace = workspace
        self.toolSharePath = os.path.dirname(scriptPath)

    # Getters for files and data directories
    @property
    def ToolDataPath(self):
        return os.path.join(self.toolSharePath, self._data_folder)

    @property
    def InputDataPath(self):
        return os.path.join(self.ToolDataPath, self._input_data)

    @property
    def AnthroFeaturePath(self):
        return os.path.join(self.ToolDataPath, self._anthro_data)

    @property
    def LayerFilePath(self):
        return os.path.join(self.toolSharePath, self._layer_files)

    # Getters for standard credit system values and objects
    @property
    def CreditTerms(self):
        return self._credit_terms

    @property
    def DebitTerms(self):
        return self._debit_terms

    @property
    def GrSGSeasons(self):
        return self._grsg_seasons

    @property
    def MuleDeerSeasons(self):
        return self._mule_deer_seasons

    @property
    def CoorSystem(self):
        inputDataPath = self.InputDataPath
        reference_layer = os.path.join(inputDataPath,
                                       self._coordinate_reference)
        coordinate_system = arcpy.Describe(reference_layer).spatialReference
        return coordinate_system

    @property
    def HabitatMgmtArea(self):
        inputDataPath = self.InputDataPath
        habitat_bounds = os.path.join(inputDataPath, self._program_scope)
        return habitat_bounds

    @property
    def GrSGHabitat(self):
        inputDataPath = self.InputDataPath
        grsg_habitat = os.path.join(inputDataPath,
                                      self._grsg_habitat_mgmt_area)
        return grsg_habitat

    @property
    def GrSGHabitatRaster(self):
        inputDataPath = self.InputDataPath
        grsg_habitat = os.path.join(inputDataPath,
                                    self._grsg_habitat_raster)
        return grsg_habitat

    @property
    def MuleDeerHabitat(self):
        inputDataPath = self.InputDataPath
        mule_deer_habitat = os.path.join(inputDataPath,
                                      self._mule_deer_habitat_mgmt_area)
        return mule_deer_habitat

    @property
    def ParameterValues(self):
        anthroFeaturePath = self.AnthroFeaturePath
        return os.path.join(anthroFeaturePath, self._parameter_table)

    @property
    def EmptyRaster(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._extent_raster))

    @property
    def AgricultureIndex(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._grsg_ag_index))

    @property
    def Lakes(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._lakes))

    # @property
    # def UrbanIndex(self):
    #     inputDataPath = self.InputDataPath
    #     return Raster(os.path.join(inputDataPath, self._urban_index))

    @property
    def LekPresenceRaster(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._lek_presence_raster))

    @property
    def LekDistanceModifier(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._lek_distance_modifier))

    @property
    def ConiferModifier(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._grsg_conifer_modifier))

    @property
    def GrSG_LDI(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._grsg_ldi))

    @property
    def SageModifier(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._lek_distance_modifier))

    @property
    def Precip(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._precip))

    @property
    def ConiferCover(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._conifer_cover))

    @property
    def BWSGHab(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._grsg_bw))

    @property
    def BWMDHab(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._mule_deer_bw))

    @property
    def MuleDeerMigrationMod(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._mule_deer_mig_mod))

    @property
    def MuleDeerWinterMod(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._mule_deer_winter_mod))

    @property
    def MuleDeerSummerMod(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._mule_deer_summer_mod))

    @property
    def MuleDeerLDI(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._mule_deer_ldi))

    @property
    def BWMD_Open(self):
        inputDataPath = self.InputDataPath
        return Raster(os.path.join(inputDataPath, self._mule_deer_open))

    # Instance methods
    def getLayerFile(self, layer_name):
        layerFilePath = self.LayerFilePath
        layer_file = os.path.join(layerFilePath, layer_name)
        return layer_file


# ----------------------------------------------------------------------------

# PROGRAM-SPECIFIC FUNCTIONS

def DetectHabitat(project_area, habitat_range):
    file_list = [project_area, habitat_range]
    overlap = arcpy.Intersect_analysis(file_list, "overlap")
    
    test = arcpy.GetCount_management(overlap)
    count = int(test.getOutput(0))

    if count > 0:
        return True
    else:
        return False

def CalcAnthroDisturbance(Parameter_Values, term, unique_proposed_subtypes,
                             anthro_disturbance_type, cheStandard,
                             dist_field, weight_field, cellSize, emptyRaster,
                             mask = None):
    """
    Calculates the anthropogenic disturbance associated with all subtypes of
    disturbance present within the Analysis Area, selects the maximum impact
    for all subtypes within each type and then multiplies those to
    calculate cumulative anthropogenic disturbance and saves to the project's
    gdb.
    :param cellSize:
    :param Anthro_Features: feature class with anthropogenic features
    :param raster_100: raster of value 100
    :param Analysis_Area: Analysis Area feature class
    :param Parameter_Values: the Parameter Values table
    :param term: string corresponding to term
    :param field: field name where Subtype is stored as a string
    :return: the name of the resulting anthropogenic disturbance raster as
    a string
    """
    # Extract lists of Types, Subtypes, Distances, and Weights
    typeList = [row[0] for row in arcpy.da.SearchCursor(
        Parameter_Values, "Type")]
    subtypeList = [row[0] for row in arcpy.da.SearchCursor(
        Parameter_Values, "Subtype")]
    distanceList = [row[0] for row in arcpy.da.SearchCursor(
        Parameter_Values, dist_field)]
    weightList = [row[0] for row in arcpy.da.SearchCursor(
        Parameter_Values, weight_field)]

    # Create dictionaries for weights and distances by subtype
    distanceDict = dict(list(zip(subtypeList, distanceList)))
    weightDict = dict(list(zip(subtypeList, weightList)))

    # Identify raster that will be used as the snap raster
    arcpy.env.snapRaster = emptyRaster

    def makeUnique(typeList):
        """Uniquify the anthropogenic feature types"""
        uniqueTypes = []
        for anthroType in typeList:
            if anthroType not in uniqueTypes:
                if anthroType != "N/A":
                    uniqueTypes.append(anthroType)
        return uniqueTypes

    def getUniqueSubtypes(uniqueType, typeList, subtypeList):
        """get unique subtypes associated with each type"""
        uniqueSubtypeList = []
        i = 0
        for t in typeList:
            if t == uniqueType:
                subtypeIndex = i
                subtype = subtypeList[subtypeIndex]
                uniqueSubtypeList.append(subtype)
            i += 1
        return uniqueSubtypeList

    def calcSubtypeDisturbance(AnthroFeatures, subtype, AnthroDisturbanceType):
        """calculate disturbance associated with each subtype"""
        distance = distanceDict[subtype]
        weight = weightDict[subtype]

        AnthroFeatures = Raster(AnthroFeatures)

        if distance > 0:
            arcpy.AddMessage("  Calculating direct and indirect effects of "
                             + str(subtype))
            outEucDist = EucDistance(AnthroFeatures, distance, cellSize)
            tmp1 = 100 - (1/(1 + Exp(((outEucDist / (distance/2))-1)*5))) * weight  # sigmoidal
            # tmp1 = (100 - (weight * Power((1 - outEucDist/distance), 2)))  # exponential
            # tmp1 = 100 - (weight - (outEucDist / distance) * weight)  # linear
            tmp2 = Con(IsNull(tmp1), 100, tmp1)
            subtypeRaster = tmp2
            subtypeRaster.save(AnthroDisturbanceType + "_" + subtype
                               + "_Subtype_Disturbance")
        elif weight > 0:
            arcpy.AddMessage("  Calculating direct effects of "
                             + str(subtype))
            tmp3 = Con(IsNull(AnthroFeatures), 0, AnthroFeatures)
            subtypeRaster = 100 - (tmp3 * weight)
            subtypeRaster.save(AnthroDisturbanceType + "_" + subtype
                               + "_Subtype_Disturbance")
        else:
            subtypeRaster = None

        return subtypeRaster

    def calcTypeDisturbance(anthroType, subtypeRasters, AnthroDisturbanceType):
        """combine anthropogenic disturbance for all subtypes of a specific type"""
        arcpy.AddMessage("   Combining effects of "
                         + str(anthroType) + " features")
        typeRaster100 = CellStatistics(subtypeRasters, "MINIMUM")
        typeRaster = typeRaster100 / 100
        typeRaster.save(AnthroDisturbanceType + "_" + anthroType
                        + "_Type_Disturbance")

        return typeRaster

    def multiplyRasters(rasterList, AnthroDisturbanceType, emptyRaster):
        """multiply type rasters to calculate overall disturbance"""
        # Define local variables
        Agriculture_Index = cheStandard.AgricultureIndex
        # Urban_Index = cheStandard.UrbanIndex
        Lakes = cheStandard.Lakes

        if AnthroDisturbanceType == "Pre" or AnthroDisturbanceType == "Post":
            if dist_field == "GrSG_Dist":  # better way of distinguishing if ag index needed
                rasterList2 = rasterList + [Agriculture_Index, Lakes]
            else:
                rasterList2 = rasterList + [Lakes]
            anthroRaster = np.prod(np.array(rasterList2))
        elif AnthroDisturbanceType == "LekDisturbanceModifier":
            rasterList2 = rasterList + [emptyRaster]
            anthroRaster = np.prod(np.array(rasterList2))

        return anthroRaster

    # Function calls
    anthro_path = cheStandard.AnthroFeaturePath
    uniqueTypes = makeUnique(typeList)
    rasterList = []
    # features = arcpy.MakeFeatureLayer_management(Anthro_Features, "lyr")
    for anthroType in uniqueTypes:
        arcpy.AddMessage(" Evaluating " + term + " "
                         + anthroType + " Indirect Disturbance")
        uniqueSubtypeList = getUniqueSubtypes(anthroType, typeList, subtypeList)
        subtypeRasters = []
        for subtype in uniqueSubtypeList:
            # where_clause = """{} = '{}'""".format(
            #     arcpy.AddFieldDelimiters(features, field), subtype)
            # arcpy.SelectLayerByAttribute_management(features, "NEW_SELECTION",
            #                                         where_clause)
            #
            # test = arcpy.GetCount_management(features)
            # count = int(test.getOutput(0))
            # # arcpy.AddMessage("   " + str(count) + " features found of subtype " +
            # #                  subtype)
            #
            # if count > 0:
            #     # Convert selected anthro features to raster to prevent losing
            #     # small features that do not align with cell centers
            #     arcpy.AddMessage("   Features detected of subtype " + subtype)
            #     AddFields(features, ["raster"], ["SHORT"])
            #     with arcpy.da.UpdateCursor(features, ["raster"]) as cursor:
            #         for row in cursor:
            #             row[0] = 1
            #             cursor.updateRow(row)
            #     value_field = "raster"
            #     out_rasterdataset = "in_memory/tmp_raster"
            #     cell_assignment = "MAXIMUM_AREA"
            #     priority_field = "raster"
            #     cellSize = arcpy.GetRasterProperties_management(
            #         raster_100, "CELLSIZEX").getOutput(0)
            #     arcpy.PolygonToRaster_conversion(features,
            #                                      value_field,
            #                                      out_rasterdataset,
            #                                      cell_assignment,
            #                                      priority_field,
            #                                      cellSize)
            #     arcpy.DeleteField_management(features, "raster")

            # Determine which anthro features rasters to use depending
            # on anthropogenic disturbance type being calculated ('pre',
            # 'post', or 'LekDisturbanceModifier')

            # For calculating pre-project anthro disturbance
            if anthro_disturbance_type == "Pre":
                AnthroFeatures = os.path.join(anthro_path, subtype)

            # For calculating post-project anthro disturbance
            elif anthro_disturbance_type == "Post":
                if subtype in unique_proposed_subtypes:
                    AnthroFeatures = "Post_" + subtype
                else:
                    AnthroFeatures = os.path.join(anthro_path, subtype)

            # For calculating Lek Disturbance Modifier
            elif anthro_disturbance_type == "LekDisturbanceModifier":
                if subtype in unique_proposed_subtypes:
                    AnthroFeatures = "Proposed_" + subtype
                else:
                    AnthroFeatures = None

            # For each subtype, calculate subtype raster
            if AnthroFeatures is not None:
                # Mask out anthro features if specified
                if mask is not None:
                    AnthroFeatures2 = Con(mask == 0, AnthroFeatures, None)
                    AnthroFeatures2.save("temp_masked_raster")
                    # AnthroFeatures = "temp_masked_raster"
                    # Calculate statistics to avoid table not found error
                    try:
                        AnthroFeatures = arcpy.CalculateStatistics_management(
                            "temp_masked_raster"
                        )
                        subtypeRaster = calcSubtypeDisturbance("temp_masked_raster",
                                                               subtype,
                                                               term)
                    except arcpy.ExecuteError:
                        subtypeRaster = None
                else:
                    subtypeRaster = calcSubtypeDisturbance(AnthroFeatures,
                                                           subtype,
                                                           term)
                if subtypeRaster is not None:
                    subtypeRasters.append(subtypeRaster)

        # For each type, combine subtype rasters to calculate type raster
        if len(subtypeRasters) > 0:
            typeRaster = calcTypeDisturbance(anthroType, subtypeRasters,
                                             term)
            rasterList.append(typeRaster)

    # Calculate combined anthropogenic disturbance raster
    anthroRaster = multiplyRasters(rasterList, anthro_disturbance_type,
                                   emptyRaster)

    # Clean up
    arcpy.Delete_management("in_memory")

    return anthroRaster


def calcWinterHabitatGRSG (anthroRaster, ConiferModifier, LDI, 
                           SuitableHabitat=None):
    
    winterHabitat = (anthroRaster 
                     * ConiferModifier 
                     * LDI)
    
    if SuitableHabitat is not None:
        winterHabitat = winterHabitat * SuitableHabitat

    return winterHabitat


def calcBreedingHabitatGRSG (anthroRaster, ConiferModifier, LDI,  
                             LekDistanceModifier, SuitableHabitat=None):
    
    breedingHabitat = (anthroRaster 
                       * ConiferModifier 
                       * LDI 
                       * LekDistanceModifier)
    
    if SuitableHabitat is not None: 
        breedingHabitat = breedingHabitat * SuitableHabitat

    return breedingHabitat


def calcSummerHabitatGRSG(anthroRaster, ConiferModifier, LDI,  
                          SageModifier, SuitableHabitat=None):
    
    summerHabitat = (anthroRaster 
                     * ConiferModifier 
                     * LDI 
                     * SageModifier)
    
    if SuitableHabitat is not None: 
        summerHabitat = summerHabitat * SuitableHabitat

    return summerHabitat


def calcSummerHabitatMD (anthroRaster, LDI, SummerModifier,
                         SuitableHabitat=None):
    
    summerHabitat = anthroRaster * LDI * SummerModifier
    
    if SuitableHabitat is not None:
        summerHabitat = summerHabitat * SuitableHabitat

    return summerHabitat


def calcMigratoryHabitatMD (anthroRaster, LDI, MigrationModifier,
                            SuitableHabitat=None):
    
    migratoryHabitat = anthroRaster * LDI * MigrationModifier
    
    if SuitableHabitat is not None:
        migratoryHabitat = migratoryHabitat * SuitableHabitat

    return migratoryHabitat


def calcWinterHabitatMD(anthroRaster, LDI, WinterModifier,
                        SuitableHabitat=None):
    
    winterHabitat = anthroRaster * LDI * WinterModifier
    
    if SuitableHabitat is not None:
        winterHabitat = winterHabitat * SuitableHabitat

    return winterHabitat


def applyLekUpliftModifierPre(preSeasonalHabitat, LekPresenceRaster):
    """make the habitat quality of the pre seasonal habtiat raster equal to 1
    wherever the Lek Presence Raster is also 1, ie a lek is present"""
    inRaster = LekPresenceRaster
    inTrueRaster = preSeasonalHabitat
    inFalseConstant = LekPresenceRaster
    whereClause = "VALUE = 0"

    LSDMpre = Con(inRaster, inTrueRaster, inFalseConstant, whereClause)
    return LSDMpre


def applyLekUpliftModifierPost(postSeasonalHabitat, LekPresenceRaster,
                               LekDisturbanceModifier):
    """make the habitat quality of the post seasonal habitat raster equal
    to the lek disturbance/uplift modifier wherever the Lek Presence Raster
    is 1, ie a lek is present"""
    inRaster = LekPresenceRaster
    inTrueRaster = postSeasonalHabitat
    inFalseConstant = LekDisturbanceModifier
    whereClause = "VALUE = 0"

    LSDMpost = Con(inRaster, inTrueRaster, inFalseConstant, whereClause)
    return LSDMpost


def calcConiferPost(coniferTreatmentArea, Conifer_Cover):
    arcpy.AddMessage("Calculating post-project conifer modifier")
    # Add field Conifer to use when converting to raster
    inTable = coniferTreatmentArea
    fieldName = "Conifer"
    fieldType = "SHORT"
    expression = 0
    arcpy.AddField_management(inTable, fieldName, fieldType)
    arcpy.CalculateField_management(inTable, fieldName, expression,
                                    "PYTHON_9.3", "")

    # Convert to raster
    in_features = coniferTreatmentArea
    value_field = "Conifer"
    out_rasterdataset = "Proposed_Conifer_Cover"
    cell_assignment = "MAXIMUM_AREA"
    priority_field = "Conifer"
    cellSize = 30

    coniferRaster = arcpy.PolygonToRaster_conversion(in_features,
                                                     value_field,
                                                     out_rasterdataset,
                                                     cell_assignment,
                                                     priority_field,
                                                     cellSize)

    # Mask existing conifer cover
    coniferPost = Con(IsNull(coniferRaster), Conifer_Cover, coniferRaster)
    coniferPost.save("Post_Conifer_Cover")

    # Calculate neighborhood statistics
    in_raster = coniferPost
    radius = 400
    neighborhood = NbrCircle(radius, "MAP")
    statistics_type = "MEAN"

    coniferCover400 = FocalStatistics(in_raster, neighborhood, statistics_type)

    # Reclassify to get Post_Conifer_Modifier
    in_raster = coniferCover400
    reclass_field = "VALUE"
    remapTable = [[0, 1, 100], [1, 2, 28], [2, 3, 14], [3, 4, 9], [4, 5, 6],
                  [5, 7, 3], [7, 8, 2], [8, 9, 1], [9, 100, 0]]
    coniferModifierPost100 = Reclassify(in_raster, reclass_field,
                                        RemapRange(remapTable))
    coniferModifierPost = Float(coniferModifierPost100) / 100

    return coniferModifierPost


def calcLekUpliftModifier(LekPresenceRaster, upliftModifierList):
    lekUpliftModifier = LekPresenceRaster
    for uplift in upliftModifierList:
        lekUpliftModifier += uplift

    return lekUpliftModifier


def calcUplift(preModifier, postModifier):
    uplift = postModifier - preModifier
    return uplift


def convertMapUnitsToRaster(projectGDB, mapUnits, season, cellSize):
    # Select features of specified subtype
    util.ClearSelectedFeatures(mapUnits)
    feature = arcpy.MakeFeatureLayer_management(mapUnits, "lyr")
    fields = ["Winter", "Breed", "Summer"]
    for field in fields:
        where_clause = "NOT {0} IS NULL".format(
                    arcpy.AddFieldDelimiters(feature, field)
                    )
        arcpy.SelectLayerByAttribute_management(feature,
                                                "ADD_TO_SELECTION",
                                                where_clause)
        
    # Count features selected to ensure >0 feature selected
    test = arcpy.GetCount_management(mapUnits)
    count = int(test.getOutput(0))    

    # Convert to raster
    if count > 0:
        in_features = mapUnits
        value_field = season
        out_rasterdataset = os.path.join(
            projectGDB, season + "_Site_Quality")
        cell_assignment = "MAXIMUM_AREA"
        priority_field = season
        
        arcpy.PolygonToRaster_conversion(in_features,
                                         value_field,
                                         out_rasterdataset,
                                         cell_assignment,
                                         priority_field,
                                         cellSize)
        return out_rasterdataset
        
        
def convertProposedToRasterCredit(anthroFeaturesRemoved, cellSize):
    arcpy.AddMessage("Preparing Proposed Surface Disturbance for processing")
    # Add field Conifer to use when converting to raster
    inTable = anthroFeaturesRemoved
    fieldName = "Weight2"
    fieldType = "SHORT"
    expression = 1
    arcpy.AddField_management(inTable, fieldName, fieldType)
    arcpy.CalculateField_management(inTable, fieldName, expression, "PYTHON_9.3", "")

    # Check feature type of provided feature class
    desc = arcpy.Describe(anthroFeaturesRemoved)

    # Make feature layer of proposed surface disturbance
    features = arcpy.MakeFeatureLayer_management(anthroFeaturesRemoved, "lyr")

    # Generate list of unique subtypes in Proposed_Surface_Disturbance
    uniqueProposedSubtypes = list(set([row[0] for row in arcpy.da.SearchCursor(
        anthroFeaturesRemoved, "Subtype")]))
    arcpy.AddMessage("Proposed Surface Disturbance contains "
                     + ", ".join(uniqueProposedSubtypes))

    for subtype in uniqueProposedSubtypes:
        # Select features of specified subtype
        field = "Subtype"
        where_clause = """{} = '{}'""".format(arcpy.AddFieldDelimiters
                                              (features, field), subtype)

        arcpy.SelectLayerByAttribute_management(features,
                                                "NEW_SELECTION",
                                                where_clause)

        # Count features selected to ensure >0 feature selected
        test = arcpy.GetCount_management(features)
        count = int(test.getOutput(0))

        # Convert to raster
        if count > 0:
            in_features = features
            value_field = "Weight"
            out_rasterdataset = os.path.join("in_memory", "Proposed_" + subtype + "Null")
            cell_assignment = "MAXIMUM_AREA"
            priority_field = "Weight"

            if desc.shapeType == "Polygon":
                arcpy.PolygonToRaster_conversion(in_features,
                                                 value_field,
                                                 out_rasterdataset,
                                                 cell_assignment,
                                                 priority_field,
                                                 cellSize)
            else:  # Consider changing to buffer of ? meters
                arcpy.FeatureToRaster_conversion(in_features,
                                                 value_field,
                                                 out_rasterdataset,
                                                 cellSize)

            # Change Null values to 0 in proposed anthro feature removed raster
            out_con = Con(IsNull(out_rasterdataset), 0, out_rasterdataset)
            out_con.save("Proposed_" + subtype)

        # Clear selected features
        arcpy.SelectLayerByAttribute_management(features, "CLEAR_SELECTION")

    return uniqueProposedSubtypes
    # The returned set of uniqueProposedSutbypes is used in
    # combineProposedWithCurrent and calcAnthroDisturbance to
    # identify which subtypes are included in the post-project
    # surface disturbance


def convertProposedToRasterDebit(ProposedSurfaceDisturbance, cellSize):
    arcpy.AddMessage("Preparing Proposed Surface Disturbance for processing")

    # Check feature type of provided feature class
    desc = arcpy.Describe(ProposedSurfaceDisturbance)

    # Make feature layer of proposed surface disturbance
    features = arcpy.MakeFeatureLayer_management(ProposedSurfaceDisturbance, "lyr")

    # Generate list of unique subtypes in Proposed_Surface_Disturbance
    uniqueProposedSubtypes = list(set([row[0] for row in arcpy.da.SearchCursor(
        ProposedSurfaceDisturbance, "Subtype")]))
    arcpy.AddMessage("Proposed Surface Disturbance contains "
                     + str(uniqueProposedSubtypes))

    for subtype in uniqueProposedSubtypes:
        # Select features of specified subtype
        field = "Subtype"
        where_clause = """{} = '{}'""".format(arcpy.AddFieldDelimiters
                                              (features, field), subtype)

        arcpy.SelectLayerByAttribute_management(features,
                                                "NEW_SELECTION",
                                                where_clause)

        # Count features selected to ensure >0 feature selected
        test = arcpy.GetCount_management(features)
        count = int(test.getOutput(0))

        # Convert to raster
        if count > 0:
            in_features = features
            value_field = "Weight"
            out_rasterdataset = os.path.join("Proposed_" + subtype)
            cell_assignment = "MAXIMUM_AREA"
            priority_field = "Weight"

            if desc.shapeType == "Polygon":
                arcpy.PolygonToRaster_conversion(in_features,
                                                 value_field,
                                                 out_rasterdataset,
                                                 cell_assignment,
                                                 priority_field,
                                                 cellSize)
            else:  # Consider changing to buffer of ? meters
                arcpy.FeatureToRaster_conversion(in_features,
                                                 value_field,
                                                 out_rasterdataset,
                                                 cellSize)

        # Clear selected features
        arcpy.SelectLayerByAttribute_management(features,
                                                "CLEAR_SELECTION")

    return uniqueProposedSubtypes
    # The returned set of uniqueProposedSutbypes is used in
    # combineProposedWithCurrent and calcAnthroDisturbanceto
    # identify which subtypes are included in the proposed
    # surface disturbance


def combineProposedWithCurrentCredit(anthroPath, uniqueProposedSubtypes):
    for subtype in uniqueProposedSubtypes:
        # Merge proposed and current feature rasters
        currentAnthroFeature = Raster(os.path.join(anthroPath, subtype))
        proposedAnthroFeature = Raster("Proposed_" + subtype)
        postAnthroFeature = SetNull(proposedAnthroFeature,
                                    currentAnthroFeature, "Value = 1")
        postAnthroFeature.save(os.path.join("Post_" + subtype))


def combineProposedWithCurrentDebit(anthroPath, uniqueProposedSubtypes):
    for subtype in uniqueProposedSubtypes:
        # Merge proposed and current feature rasters
        currentAnthroFeature = Raster(os.path.join(anthroPath, subtype))
        proposedAnthroFeature = Raster("Proposed_" + subtype)
        postAnthroFeature = Con(IsNull(proposedAnthroFeature),
                                currentAnthroFeature, proposedAnthroFeature)
        postAnthroFeature.save(os.path.join("Post_" + subtype))


def calcAverageHabitatQuality(seasonalHabitatRasters):
    statisticsType = "MEAN"
    ignoreNoData = "DATA"
    averageRaster = CellStatistics(seasonalHabitatRasters, statisticsType,
                                   ignoreNoData)
    return averageRaster


def calcDebits(DebitProjectArea, pre_field, post_field, out_field):
    # Add field for debits
    inTable = DebitProjectArea
    fieldName = out_field
    fieldType = "DOUBLE"

    arcpy.AddField_management(inTable, fieldName, fieldType)

    # Calculate debits
    with arcpy.da.UpdateCursor(DebitProjectArea, ["Acres",
                                                  pre_field,
                                                  post_field,
                                                  out_field]) as cursor:
        for row in cursor:
            row[3] = row[0] * (row[1] - row[2])
            cursor.updateRow(row)
            arcpy.AddMessage("Functional Acre difference from {} to {} is "
                             "equal to {}".format(pre_field, post_field,
                                                  row[3]))


def calcImpact(finalPreCumulative, finalPostCumulative):
    debitImpact = finalPreCumulative - finalPostCumulative
    return debitImpact
