import datetime
import os
import sys
import fiona
from fiona.crs import from_epsg
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from collections import OrderedDict
from pyproj import Proj, transform

####### BAD VERY BAD (something to do with calling pyproj.transform (or pyproj.Proj.__init__))
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
####### END BAD

# static_path = "test/static"
# data_path = "test/data"
# results_path="test/results"

# clip_filepath = os.path.join(static_path, 'northern_italy.shp')
# admin_filepath = os.path.join(static_path,'ne_10m_admin_1_states_provinces.shp')

# inputfile = os.path.join(data_path,'MODIS_C6_Europe_48h.shp')

# #outputfile = os.path.join(results_path,"FIRE.shp")


# def cleanup():
#     for file in os.listdir(results_path):
#         # print("Deleting '%s'"%file)
#         os.remove(os.path.join(results_path,file))


def Get_Fire_Hotspots(inputfile, sensor, regionfile, adminfile, outputdir):
    print("--------------------------------------------------------------------------------")
    print("Processing hotspots for %s"%sensor)

    outputfile = os.path.join(outputdir,"%s-FIRE.shp"%sensor)
   
    print("Input file = %s"%inputfile)
    print("Output file = %s"%outputfile)
    print("Region file = %s"%regionfile)
    print("Admin file = %s"%adminfile)
   
    ## create a new target shape file
    ## check https://fiona.readthedocs.io/en/stable/manual.html#writing-new-files-from-scratch for general algorithm
    ## get hotspots and write each new hotspot feature to this shape file
    with fiona.open(
        outputfile, 'w',
        driver='ESRI Shapefile',
        crs=from_epsg(4326),
        schema = {
            'geometry': 'Point',
            'properties': OrderedDict([
                ('ADM1', 'str'),
                ('ADM2', 'str'),
                ('FRP', 'float'),
                ('DATE', 'str'),
                ('TIME', 'str')
            ])
        }) as dst:

        ## get hotspots
        ## this functions writes the hotspot features to the file
        start = datetime.datetime.now()
        get_hotspots(sensor, inputfile, dst, regionfile, adminfile)
        stop = datetime.datetime.now()
        print("Time elampsed = %6.1f seconds"%(stop-start).total_seconds())
        print("--------------------------------------------------------------------------------")

    return outputfile



def get_hotspots(sensor, input_file, dst, regionfile, adminfile):
    clip_collection = fiona.open(regionfile)
    admin_collection = fiona.open(adminfile)

    nhotspots=0


    ## open SHP file contaning hotspots to be processed
    with fiona.open(input_file) as sensor_collection:
        ## get matching hotspot with corresponding properties (i.e. date, time & frp)
        ## looping over hotspots with additional information gathering (e.g. clipping) takes approx. 2.5 seconds per hotspot
        for hotspot, hotspot_properties in get_input_hotspot(sensor, sensor_collection):
            hotspot_date, hotspot_time, hotspot_frp = hotspot_properties

            ## get matching hotspots
            ## clip_feature is obsolete but returned due to settings of the function
            for clip_feature, hotspot in intersect_aoi(clip_collection, hotspot):
            
                ## get information of administrative boundary if hotspot intersects this area
                for admin_feature, hotspot in intersect_aoi(admin_collection, hotspot):

                    nhotspots+=1
                    ## get country & region name of the adminstrative boundary
                    country = admin_feature['properties']['admin']
                    region = admin_feature['properties']['name_en']

                    ## write matching hotspot information to target feature
                    results = {
                        'geometry': {
                            'type': 'Point',
                            'coordinates': (hotspot.x, hotspot.y)
                        },
                        'properties': OrderedDict([
                            ('ADM1', country),
                            ('ADM2', region),
                            ('FRP', hotspot_frp),
                            ('DATE', hotspot_date),
                            ('TIME', hotspot_time)
                        ])
                    }

                    ## append feature to target shape file
                    dst.write(results)
    clip_collection.close()
    admin_collection.close()
    print("Number of hotspots found: %d"%nhotspots)


def get_input_hotspot(sensor, collection):
    for feature in collection:
        ## get hotspot as a shapely POINT feature
        ## get hotspots with a certain confidence
        hotspot = get_hotspot_feature(sensor, feature, collection.crs)

        if hotspot:
            yield hotspot, get_hotspot_properties(feature)

def get_hotspot_feature(sensor, feature, crs):
    ## get coordinates of current hotspot
    x_coord, y_coord = feature['geometry']['coordinates']
  

    ## transform coordinates to WGS84
    target_x_coord, target_y_coord = transform(Proj(crs),Proj('EPSG:4326'),x_coord,y_coord)

    ## convert hotspot to shapely POINT feature
    ## POINT class is described here: https://shapely.readthedocs.io/en/latest/manual.html#Point
    hotspot = Point(target_y_coord, target_x_coord)

    ## get confidence level of hotspot
    ## confidence description is sensor specific
    hotspot_confidence = get_hotspot_confidence(feature, sensor)

    ## only take hotspots with a certain minimum confidence
    if hotspot_confidence > 50:
        return hotspot



def get_hotspot_confidence(feature, sensor):
    ## get confidence value of hotspot
    ## confidence value is sensor specific
    confidence = dict(feature['properties'])['CONFIDENCE']

    ## VIIRS confidence is descriptive
    ## convert to int values
    if sensor == 'VIIRS':
        if confidence == 'low':
            hotspot_confidence = 40
        elif confidence == 'nominal':
            hotspot_confidence = 60
        else:
            ## confidence == 'high'
            hotspot_confidence = 80

    ## MODIS confidence is given as int already
    elif sensor == "MODIS":
        ## sensor == 'modis'
        hotspot_confidence = int(confidence)
    else:
        raise Exception("Unknown sensor %s"%sensor)

    return hotspot_confidence


def get_hotspot_properties(feature):
    ## retrieve date, time and frp fields and write to final result
    ## fields must be present
    ## any change can corrupt the procedure
    hotspot_date = str(dict(feature['properties'])['ACQ_DATE'])
    hotspot_time = str(dict(feature['properties'])['ACQ_TIME'])
    hotspot_frp = str(dict(feature['properties'])['FRP'])

    return hotspot_date, hotspot_time, hotspot_frp


def intersect_aoi(collection, hotspot):
    for feature in collection:
        if hotspot.intersects(shape(feature['geometry'])):
            yield feature, hotspot


# if __name__ == "__main__":
#     cleanup()

#     Get_Fire_Hotspots()

#     Get_Fire_Hotspots(inputfile="data/viirs/VNP14IMGTDL_NRT_Europe_48h.shp",sensor="VIIRS")