#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
import datetime
import requests as r
from bottle.bottle import route, run, template, post, request

import logger

logger.configFile = "../config.ini"

log = logger.getLogger("traffic-helper-service")
host = "http://traffic22.ru/php"


class TrafficClient:
    def __int__(self):
        pass

    def getAllRoutes(self):
        routes = r.get("%s/getRoutes.php" % host, params={"city": "barnaul"})
        if routes.status_code == 200:
            return routes.json()
        else:
            raise Exception("Can't get route info: %s (status %s)" % (routes.content, routes.status_code))

    def getVehiclesForRoute(self, routeIds):
        vehicles = r.get("%s/getVehiclesMarkers.php" % host,
                         params={"rids": routeIds, "lat0": 0, "lat1": 90, "lng0": 0, "lng1": 90, "city": "barnaul", "curk": 0})
        if vehicles.status_code == 200:
            return vehicles.json()
        else:
            raise Exception("Can't get vehicle info: %s (status %s)" % (vehicles.content, vehicles.status_code))

    def getVehicleForecasts(self, vehicleId, type):
        vehicleForecasts = r.get("%s/getVehicleForecasts.php" % host, params={"vid": vehicleId, "type": type, "city": "barnaul"})
        if vehicleForecasts.status_code == 200:
            return vehicleForecasts.json()
        else:
            raise Exception("Can't get vehicle info: %s (status %s)" % (vehicleForecasts.content, vehicleForecasts.status_code))

    def getAllStations(self):
        stations = r.get("%s/getStations.php" % host, params={"city": "barnaul"})
        if stations.status_code == 200:
            return stations.json()
        else:
            raise Exception("Can't get route info: %s (status %s)" % (stations.content, stations.status_code))


def getTrumInfo():
    result = []
    routes = client.getAllRoutes()
    routeOfTram10OnPotok = filter(lambda x: x.get("type") == u"Тр" and x.get("tostid") == 59, routes)

    routeIds = ",".join(map(lambda x: unicode(x.get("id")) + u"-1", routeOfTram10OnPotok))

    vehicles = client.getVehiclesForRoute(routeIds)

    for vehs in vehicles.get(u"anims", []):
        vehiclesForecasts = client.getVehicleForecasts(vehs.get(u"id"), 1)
        for station in vehiclesForecasts:
            if station.get(u"stid") == u"132":
                myStation = filter(lambda x: x.get(u"stid") == u"126", vehiclesForecasts)[0]
                result.append(u"Нужно выходить через %s минут чтоб успеть на трамвай №%s, который должен быть на остановке в %s" % (
                    station.get(u"arrt") / 60, vehs.get(u"gos_num"), datetime.datetime.now() + datetime.timedelta(seconds=myStation.get(u"arrt"))))
                break

    return result


@route("/tram_info")
def is_avaliable():
    return "\n".join(map(lambda x: "<pre>" + x + "</pre>", getTrumInfo()))


if __name__ == '__main__':
    log.info("Start service")
    client = TrafficClient()
    try:
        run(host="0.0.0.0", port="12345")
    except Exception, e:
        log.error("Error while exec: %s", e.message)
        log.exception("Exeptiong while exec: ")
