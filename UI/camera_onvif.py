from onvif import ONVIFCamera

import time

camera_ip = "10.10.176.19" # cam3: "10.10.176.17"
onvif_port = 8000
username = "admin"
password = "Xray@12345;"

cam = ONVIFCamera(camera_ip, onvif_port, username, password)
media_service = cam.create_media_service()
profiles = media_service.GetProfiles()

profile = profiles[0]
# print(f"Profiles: {profiles[0]}")

ptz = cam.create_ptz_service()


# # Move the camera to the right
# move_req = ptz.create_type('ContinuousMove')
# move_req.ProfileToken = profile.token

# move_req.Velocity = {
#     'PanTilt': {
#         'space': 'http://www.onvif.org/ver10/tptz/PanTiltSpaces/VelocityGenericSpace',
#         'x': 0.5,
#         'y': 0.0
#     },
#     'Zoom': {
#         'space': 'http://www.onvif.org/ver10/tptz/ZoomSpaces/VelocityGenericSpace',
#         'x': 0.0
#     }
# }

# ptz.ContinuousMove(move_req)

# # Move for 2 seconds, then stop
# time.sleep(2)
# ptz.Stop({'ProfileToken': profile.token})

# -- Pan Right for 1 second --
move_req = ptz.create_type('ContinuousMove')
move_req.ProfileToken = profile.token
move_req.Velocity = {
    'PanTilt': {
        'space': 'http://www.onvif.org/ver10/tptz/PanTiltSpaces/VelocityGenericSpace',
        'x': 0.1,  # slow right
        'y': 0.0
    },
    'Zoom': {
        'space': 'http://www.onvif.org/ver10/tptz/ZoomSpaces/VelocityGenericSpace',
        'x': 0.0   # no zoom
    }
}
ptz.ContinuousMove(move_req)
time.sleep(1)
ptz.Stop({'ProfileToken': profile.token})

# -- Pan Left for 1 second --
move_req.Velocity['PanTilt']['x'] = -0.1  # slow left
ptz.ContinuousMove(move_req)
time.sleep(1)
ptz.Stop({'ProfileToken': profile.token})

# -- Approx. re-center (0.5s to the right) --
move_req.Velocity['PanTilt']['x'] = 0.1
ptz.ContinuousMove(move_req)
time.sleep(0.5)
ptz.Stop({'ProfileToken': profile.token})

# -- Zoom In for 1 second --
move_req.Velocity['PanTilt']['x'] = 0.0
move_req.Velocity['PanTilt']['y'] = 0.0
move_req.Velocity['Zoom']['x'] = 0.1
ptz.ContinuousMove(move_req)
time.sleep(1)
ptz.Stop({'ProfileToken': profile.token})

# -- Zoom Out for 1 second --
move_req.Velocity['Zoom']['x'] = -0.1
ptz.ContinuousMove(move_req)
time.sleep(1)
ptz.Stop({'ProfileToken': profile.token})

print("Completed ~5 seconds of slow pan & zoom operations.")

