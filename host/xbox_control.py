import time
import math
import threading

from cc.xboxcontroller import XboxController, Hand, Button
import recoil


# TRANSPORT = "/dev/ttyACM0"
TRANSPORT = "COM14"
# TRANSPORT = "COM32"


class Humanoid:
    def __init__(self, transport):
        self.transport = recoil.SerialCANTransport(port=transport, baudrate=115200)
        self.is_stopped = threading.Event()
        
        self.joints = [
            recoil.MotorController(self.transport, device_id=1),
            recoil.MotorController(self.transport, device_id=2),
            recoil.MotorController(self.transport, device_id=3),
            recoil.MotorController(self.transport, device_id=4),
            recoil.MotorController(self.transport, device_id=5),
            recoil.MotorController(self.transport, device_id=6),
            recoil.MotorController(self.transport, device_id=7),
            recoil.MotorController(self.transport, device_id=8),
            recoil.MotorController(self.transport, device_id=9),
            recoil.MotorController(self.transport, device_id=10),
            recoil.MotorController(self.transport, device_id=11),
            recoil.MotorController(self.transport, device_id=12),
        ]
        
        self.torque_limit = 0.5

        self.target_positions = [0] * 12
        self.current_positions = [0] * 12

    def start(self):
        self.transport.start()
        self.is_stopped.clear()

    def stop(self):
        self.is_stopped.set()
        print("stopping...")

    def resetTargetPositions(self):
        for i, j in enumerate(self.joints):
            self.target_positions[i] = j.getPositionMeasured()
        self.printPositions()
        
    def printPositions(self):
        for i, j in enumerate(self.joints):
            print("{0}: {1:.3f}".format(j.device_id, self.target_positions[i]), end="\t")
        print()

    def setDamping(self):                
        for j in self.joints:
            j.setMode(recoil.Mode.DAMPING)
        
    def setIdle(self):
        for j in self.joints:
            j.setMode(recoil.Mode.IDLE)

    def rampUp(self):
        print("ramping up position control...")
        
        for i, j in enumerate(self.joints):
            j.setPositionTarget(self.target_positions[i])
            j.setTorqueLimit(0)
            j.setMode(recoil.Mode.POSITION)

        ramp_up_time_ms = 1
        dt = 0.01
        n_counts = int(ramp_up_time_ms / dt)
        for t in range(n_counts):
            try:
                if self.is_stopped.is_set():
                    return
                ramp_torque_limit = self.torque_limit * (t / n_counts)

                for i, j in enumerate(self.joints):
                    j.setPositionTarget(self.target_positions[i])
                    j.setTorqueLimit(ramp_torque_limit)
                    j.feed()
                        
                print("{:.3f} / {:.3f}".format(ramp_torque_limit, self.torque_limit))

                time.sleep(dt)
            except KeyboardInterrupt:
                self.stop()
                continue
    
    def update(self):
        for i, j in enumerate(self.joints):
            j.setPositionTarget(self.target_positions[i])
            j.feed()


robot = Humanoid(transport=TRANSPORT)
stick = XboxController(0, deadzone=0.)

active_joint = 0

def onButton(button, pressed):
    global active_joint
    if not pressed:
        return
    if button != Button.DPAD_L and button != Button.DPAD_R:
        return
    
    if button == Button.DPAD_L:
        if active_joint > 0:
            active_joint -= 1
    if button == Button.DPAD_R:
        if active_joint < (len(robot.joints) - 1):
            active_joint += 1
    print("current active controller: {}".format(robot.joints[active_joint].device_id))


robot.start()

robot.resetTargetPositions()

stick.onButton = onButton

while not robot.is_stopped.is_set():
    try:
        stick.update()
        robot.update()
    
        if stick.getXButton():
            robot.setDamping()
            robot.stop()
        elif stick.getAButton():
            # blocking
            robot.rampUp()

        robot.target_positions[active_joint] += 0.2 * stick.axes["LY"]
        robot.printPositions()

        time.sleep(0.01)
            
    except KeyboardInterrupt:
        robot.stop()
        print("keyboard interrupted")

print("Dampen mode")

robot.setDamping()

# add a 1 second delay to allow button debouncing
for i in range(100):
    stick.update()
    robot.update()
    time.sleep(0.01)

print("Press X again to shut down")

while not stick.getXButton():
    try:
        stick.update()
        robot.update()
    except KeyboardInterrupt:
        break


robot.setIdle()
robot.setIdle()
print("robot stopped")

robot.transport.stop()
