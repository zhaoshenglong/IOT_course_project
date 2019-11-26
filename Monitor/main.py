import time
from typing import Dict
import serial
from yaml import load
from enum import Enum, unique
from monitor import Monitor
from request import Request
from shutil import copy
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from detect_response_process import *


@unique
class Property(Enum):
    Warning = "Warning"
    Temperature = "Temperature"
    Humidity = "Humidity"
    Camera = "Camera"


def main():
    config: Dict
    with open("./config.yaml", 'r') as f:
        config = load(f, Loader)

    monitor = Monitor(config)
    monitor.open()
    req = Request(config)
    img_path = config["image"]["path"]
    img_name = config["image"]["new_name"]
    classes = load_classes(config["classes"])
    warning: int
    while True:
        start = time.time()  # 获取开始时间
        temperature, humidity, shake = monitor.get_state()
        monitor.print_state()
        if shake == 1:
            monitor.shake = 0
        
        # post object detection and get warning
        obj_detect_rsp = req.post_object_detect()
        try:
            if obj_detect_rsp["success"]:
                print("Request success\n")
                for img_i, img_dic in enumerate(obj_detect_rsp["detections"]):
                    print("(%d) Image: '%s'" % (img_i, img_dic["img_path"]))
                    if img_dic["img_detection"] is not None:
                        for x1, y1, x2, y2, conf, cls_conf, cls_pred in img_dic["img_detection"]:
                            if int(cls_pred) == int(config["target"]):
                                box_w = x2 - x1 # Bounding Box的宽度
                                box_h = y2 - y1 # Bounding Box的高度
                                print("\t+ Label: %s, Conf: %.5f" % (classes[int(cls_pred)], cls_conf))
                                print("\t  (x1, y1) = (%.2f, %.2f)" % (x1, y1)) 
                                print("\t  (x2, y2) = (%.2f, %.2f)" % (x2, y2))
                                print("\t  width = %.2f, height = %.2f" % (box_w, box_h))
       
            warning = detect_response_process(shake, obj_detect_rsp, classes[int(config["target"])])
        except KeyError as ke:
            print("request failed")
            warning = 7 if shake == 1 else 3
        if warning == 7 or warning == 2:
            copy("/tmp/images/file-new.jpg", "/tmp/images/file-old.jpg")
            print("%s meved\n" % classes[int(config["target"])])
        print(req.post_property(Property.Warning.name, "%d%d%d" % (warning / 4 % 4, warning / 2 % 2, warning & 1)))
        print(req.post_property(Property.Temperature.name, temperature))
        print(req.post_property(Property.Humidity.name, humidity))

        # post picture
        print(req.post_picture(Property.Camera.name, "%s/%s" % (img_path, img_name)))

        
        end = time.time()  # 获取结束时间
        remain = int(config["interval"]) - int(end - start)
        if remain > 0:
            time.sleep(remain)


if __name__ == "__main__":
    main()
