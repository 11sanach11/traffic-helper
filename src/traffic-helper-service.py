#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pip install pytelegrambotapi

import os
import threading
import time

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

import datetime
import argparse
import ConfigParser

import requests as r
from bottle.bottle import route, run, request, response, install
import telebot

import logger

parser = argparse.ArgumentParser()
parser.add_argument("--config", dest="config", help='part to config.ini file, default is ../config.ini')
parser.set_defaults(config="../config.ini")
parser.add_argument("--port", type=int, dest="port", help='service listen port, default 12345')
parser.set_defaults(port=12345)

args = parser.parse_args()
configFile = args.config
port = args.port

logger.configFile = configFile

config = ConfigParser.RawConfigParser()
config.read((configFile))

log = logger.getLogger("traffic-helper-service")
host = "http://traffic22.ru/php"

telegramToken = config.get("TELEGRAM", "token")
ownId = config.getint("TELEGRAM", "own_id")
bot = telebot.TeleBot(telegramToken)


class TrafficClient:
    def __int__(self):
        pass

    def getAllRoutes(self):
        routes = r.get("%s/getRoutes.php" % host, params={"city": "barnaul"}, timeout=3)
        if routes.status_code == 200:
            return routes.json()
        else:
            raise Exception("Can't get route info: %s (status %s)" % (routes.content, routes.status_code))

    def getVehiclesForRoute(self, routeIds):
        vehicles = r.get("%s/getVehiclesMarkers.php" % host,
                         params={"rids": routeIds, "lat0": 0, "lat1": 90, "lng0": 0, "lng1": 90, "city": "barnaul", "curk": 0}, timeout=3)
        if vehicles.status_code == 200:
            return vehicles.json()
        else:
            raise Exception("Can't get vehicle info: %s (status %s)" % (vehicles.content, vehicles.status_code))

    def getVehicleForecasts(self, vehicleId, type):
        vehicleForecasts = r.get("%s/getVehicleForecasts.php" % host, params={"vid": vehicleId, "type": type, "city": "barnaul"}, timeout=3)
        if vehicleForecasts.status_code == 200:
            return vehicleForecasts.json()
        else:
            raise Exception("Can't get vehicle info: %s (status %s)" % (vehicleForecasts.content, vehicleForecasts.status_code))

    def getAllStations(self):
        stations = r.get("%s/getStations.php" % host, params={"city": "barnaul"}, timeout=3)
        if stations.status_code == 200:
            return stations.json()
        else:
            raise Exception("Can't get route info: %s (status %s)" % (stations.content, stations.status_code))


def getTrumInfo(type, myStationId, myStationEndId, goutStationId, goutStationEndId):
    result = []
    routes = client.getAllRoutes()
    routeOfTram10OnPotok = filter(lambda x: x.get("type") == type and (x.get("tostid") == int(myStationEndId) or x.get("tostid") == int(goutStationEndId)),
                                  routes)

    routeIds = ",".join(map(lambda x: unicode(x.get("id")) + u"-1", routeOfTram10OnPotok))

    vehicles = client.getVehiclesForRoute(routeIds)

    for vehs in vehicles.get(u"anims", []):
        vehiclesForecasts = client.getVehicleForecasts(vehs.get(u"id"), 1)
        stations = filter(lambda x: x.get(u"stid") == goutStationId or x.get(u"stid") == myStationId, vehiclesForecasts)
        gouotStationExists = False
        goutStation = {};
        myStation = {};
        if stations:
            if len(stations) == 2:
                gouotStationExists = True
                goutStation = filter(lambda x: x.get(u"stid") == goutStationId, stations)[0]
                myStation = filter(lambda x: x.get(u"stid") == myStationId, stations)[0]
            elif len(stations) == 1:
                neededStatidon = stations[0]
                if neededStatidon[u"stid"] == goutStationId:
                    gouotStationExists = True
                    goutStation = neededStatidon
                elif neededStatidon[u"stid"] == myStationId:
                    myStation = neededStatidon
            if gouotStationExists:
                myStationTime = datetime.datetime.now() + datetime.timedelta(seconds=myStation.get(u"arrt")) if myStation.get(
                    u"arrt") else datetime.datetime.now() + datetime.timedelta(seconds=goutStation.get(u"arrt", 0) + 300)
                result.append(
                    {
                        "time": goutStation[u"arrt"],
                        "message": u"Нужно выходить через %s минут в %s чтоб успеть на %s №%s, который должен быть на остановке в %s" % (
                            goutStation.get(u"arrt") / 60,
                            (datetime.datetime.now() + datetime.timedelta(seconds=goutStation.get(u"arrt", 0))).strftime("%H:%M:%S"),
                            vehs.get(u"rtype"), vehs.get(u"rnum"), myStationTime.strftime("%H:%M:%S"))
                    })
            else:
                result.append(
                    {
                        "time": myStation[u"arrt"],
                        "message": u"%s №%s будет на нужной остановке через %s минут в %s" % (
                            vehs.get(u"rtype"), vehs.get(u"rnum"), myStation.get(u"arrt", 0) / 60, (
                                datetime.datetime.now() + datetime.timedelta(seconds=myStation.get(u"arrt", 0))).strftime("%H:%M:%S"))
                    })

    return result


@route("/tram_info/morning")
def getTramOnMorning():
    tramInfo = getTrumInfo(type=u"Тр", myStationId=u"126", myStationEndId=u"59", goutStationId=u"132", goutStationEndId=u"59")
    return "\n".join(map(lambda x: "<pre>" + x["message"] + "</pre>", sorted(tramInfo, key=lambda x: x["time"])))


@route("/tram_info/evening")
def getTramOnEvening():
    tramInfo = getTrumInfo(type=u"Тр", myStationId=u"80", myStationEndId=u"215", goutStationId=u"139", goutStationEndId=u"59")
    return "\n".join(map(lambda x: "<pre>" + x["message"] + "</pre>", sorted(tramInfo, key=lambda x: x["time"])))


@route("/tram_info")
def isAvaliable():
    currentHour = datetime.datetime.now().hour
    if 6 <= currentHour and currentHour <= 11:
        return u"Утренний трамвай: \n" + getTramOnMorning()
    elif 15 <= currentHour and currentHour <= 22:
        return u"Вечерний трамвай: \n" + getTramOnEvening()

    return u"Неизвестное время..."


# bottle access to log file plugin
def bootleLogger(func):
    def wrapper(*args, **kwargs):
        log.debug('%s %s %s %s' % (request.remote_addr, request.method, request.url, response.status))
        req = func(*args, **kwargs)
        return req

    return wrapper


@bot.message_handler(content_types=["text"])
def repeat_all_messages(message):  # Название функции не играет никакой роли, в принципе
    log.info(u"Request: %s", message)
    if message.chat.id != ownId:
        bot.send_message(message.chat.id, "Sorry, it's private party...")
    else:
        bot.send_message(message.chat.id, isAvaliable())


def run_telegram():
    try:
        bot.polling(none_stop=True)
    except Exception,e:
        log.error("Error while exec: %s", e.message)
        log.exception("Exeptiong while exec: ")
        time.sleep(10)
        telegram_thread = threading.Thread(target=run_telegram)
        telegram_thread.setDaemon(True)
        telegram_thread.start()

def run_http():
    try:
        run(server="paste", host="0.0.0.0", port=port)
    except Exception, e:
        log.error("Error while exec: %s", e.message)
        log.exception("Exeptiong while exec: ")
        time.sleep(10)
        http_thread = threading.Thread(target=run_http)
        http_thread.setDaemon(True)
        http_thread.start()

if __name__ == '__main__':
    install(bootleLogger)
    log.info("Start service on port: %s", port)
    client = TrafficClient()
    # print (getTramOnMorning())
    # print (getTramOnEvening())
    # exit()

    http_thread = threading.Thread(target=run_http)
    http_thread.setDaemon(True)
    http_thread.start()
    telegram_thread = threading.Thread(target=run_telegram)
    telegram_thread.setDaemon(True)
    telegram_thread.start()

    time.sleep(999999999999)
