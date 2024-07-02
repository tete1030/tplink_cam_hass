import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'tplink_cam', 'lib'))
from camera import TPLinkIPCam44AW

def test_cam():
    cam = TPLinkIPCam44AW(
        "http://192.168.X.X",
        "admin",
        "XXXXXX",
        True)
    cam.login()

if __name__ == '__main__':
    test_cam()
