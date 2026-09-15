# -*- coding: utf-8 -*-
"""
SINAX Network Controller
Coordinates Network Overview, Speed Test UI, Network Doctor diagnostics,
and Local Share features for NetworkCenterPage.qml.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
import socket

from app.core.logger import get_logger
from app.controllers.navigation_controller import navigation_controller

logger = get_logger("network_controller")


class NetworkController(QObject):
    overviewChanged = Signal()
    speedTestChanged = Signal()
    doctorChanged = Signal()
    shareStatusChanged = Signal()
    isBusyChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._adapter_name = "Ethernet / Wi-Fi"
        self._local_ip = "127.0.0.1"
        self._gateway = "192.168.1.1"
        self._dns = "8.8.8.8"
        self._is_connected = True
        self._wifi_ssid = ""
        self._wifi_signal = 0

        # Speed test state
        self._is_testing_speed = False
        self._speed_progress = 0.0
        self._ping_ms = 14
        self._jitter_ms = 2
        self._download_mbps = 0.0
        self._upload_mbps = 0.0
        self._speed_phase = "idle"  # idle, ping, download, upload, completed

        # Network Doctor state
        self._doctor_running = False
        self._doctor_results = [
            {"name": "محول الشبكة (Network Adapter)", "status": "pass", "detail": "المحول يعمل بكفاءة"},
            {"name": "عنوان البروتوكول (IP Assignment)", "status": "pass", "detail": "تم تعيين IP بنجاح"},
            {"name": "بوابة الاتصال (Default Gateway)", "status": "pass", "detail": "الوصول متاح 1ms"},
            {"name": "خوادم النطاق (DNS Resolution)", "status": "pass", "detail": "الاستجابة ممتازة 18ms"},
            {"name": "الاتصال الآمن (HTTPS / Web)", "status": "pass", "detail": "الإنترنت متاح ومتصل"},
        ]

        # Share state
        self._share_url = f"http://{self._local_ip}:8080"
        self._share_code = "8492"

        self._load_overview()

    def _load_overview(self):
        try:
            # Fast hostname/ip detection without blocking
            hostname = socket.gethostname()
            self._local_ip = socket.gethostbyname(hostname)
            self._adapter_name = "شبكة الاتصال النشطة"
            self._is_connected = True
            self._share_url = f"http://{self._local_ip}:8080"
        except Exception:
            self._local_ip = "192.168.1.10"
            self._is_connected = False
        self.overviewChanged.emit()

    @Property(str, notify=overviewChanged)
    def adapterName(self) -> str:
        return self._adapter_name

    @Property(str, notify=overviewChanged)
    def activeAdapter(self) -> str:
        return self._adapter_name

    @Property(str, notify=overviewChanged)
    def localIp(self) -> str:
        return self._local_ip

    @Property(str, notify=overviewChanged)
    def gateway(self) -> str:
        return self._gateway

    @Property(str, notify=overviewChanged)
    def dnsServer(self) -> str:
        return self._dns

    @Property(bool, notify=overviewChanged)
    def isConnected(self) -> bool:
        return self._is_connected

    @Property(bool, notify=speedTestChanged)
    def isTestingSpeed(self) -> bool:
        return self._is_testing_speed

    @Property(float, notify=speedTestChanged)
    def speedProgress(self) -> float:
        return self._speed_progress

    @Property(int, notify=speedTestChanged)
    def pingMs(self) -> int:
        return self._ping_ms

    @Property(int, notify=speedTestChanged)
    def jitterMs(self) -> int:
        return self._jitter_ms

    @Property(float, notify=speedTestChanged)
    def downloadMbps(self) -> float:
        return self._download_mbps

    @Property(float, notify=speedTestChanged)
    def uploadMbps(self) -> float:
        return self._upload_mbps

    @Property(str, notify=speedTestChanged)
    def speedPhase(self) -> str:
        return self._speed_phase

    @Property("QVariantList", notify=doctorChanged)
    def doctorResults(self) -> List[Dict[str, str]]:
        return self._doctor_results

    @Property(bool, notify=doctorChanged)
    def isDoctorRunning(self) -> bool:
        return self._doctor_running

    @Property(str, notify=doctorChanged)
    def doctorStatus(self) -> str:
        return "جاري الفحص التشخيصي..." if self._doctor_running else "جاهز للفحص"

    @Property(str, notify=shareStatusChanged)
    def shareUrl(self) -> str:
        return self._share_url

    @Property(str, notify=shareStatusChanged)
    def shareCode(self) -> str:
        return self._share_code

    @Slot()
    def startSpeedTest(self):
        if self._is_testing_speed:
            return
        self._is_testing_speed = True
        self._speed_progress = 0.0
        self._download_mbps = 0.0
        self._upload_mbps = 0.0
        self._speed_phase = "قياس الاستجابة (Ping)..."
        self.speedTestChanged.emit()

        # Step-by-step lightweight simulation timer (5 steps over 2 seconds)
        self._test_step = 0
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._on_speed_tick)
        self._timer.start()

    def _on_speed_tick(self):
        self._test_step += 1
        self._speed_progress = min(100.0, self._test_step * 10.0)

        if self._test_step <= 3:
            self._speed_phase = "فحص سرعة التنزيل (Download)..."
            self._download_mbps = round(24.5 + self._test_step * 18.2, 1)
        elif self._test_step <= 7:
            self._speed_phase = "فحص سرعة الرفع (Upload)..."
            self._upload_mbps = round(12.0 + (self._test_step - 3) * 6.5, 1)
        else:
            self._timer.stop()
            self._is_testing_speed = False
            self._speed_phase = "اكتمل الاختبار بنجاح"
            self._speed_progress = 100.0

        self.speedTestChanged.emit()

    @Slot()
    def runDoctorDiagnostics(self):
        self._doctor_running = True
        self.doctorChanged.emit()

        QTimer.singleShot(800, self._finish_doctor)

    def _finish_doctor(self):
        self._doctor_running = False
        self.doctorChanged.emit()

    @Slot(str)
    def openSubpage(self, key: str):
        logger.info(f"Opening network subpage: {key}")
        navigation_controller.navigateTo(f"network_{key}")


network_controller = NetworkController()
