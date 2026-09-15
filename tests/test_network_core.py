# -*- coding: utf-8 -*-
"""
SINAX Network & Internet Center Unit Test Suite (Phase 12)
Validates core services: NetworkInfo, Speedtest, Network Doctor, Wi-Fi Analyzer,
LAN Discovery, Connections, DNS, Pure-Python QR Generator, Tools & Support Reports,
and Adapters/Routing Service.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.network.adapter_service import AdapterService
from app.services.network.connection_service import ConnectionService
from app.services.network.dns_service import POPULAR_DNS_SERVERS, DnsService
from app.services.network.doctor_service import NetworkDoctorService
from app.services.network.lan_discovery_service import LanDiscoveryService
from app.services.network.network_db import NetworkDatabase
from app.services.network.network_info_service import NetworkInfoService
from app.services.network.network_models import (
    DiagnosticCheckStage,
    DoctorDiagnosticReport,
    NearbyWifiNetwork,
    NetworkAdapterInfo,
    PublicIPInfo,
    SpeedTestResult,
)
from app.services.network.network_tools_service import COMMON_DIAGNOSTIC_PORTS, NetworkToolsService
from app.services.network.qr_generator import QrCodeGenerator, _generate_qr_svg_or_matrix
from app.services.network.speedtest_service import SpeedTestService
from app.services.network.wifi_service import WifiService


class TestNetworkCore(unittest.TestCase):
    """Unit tests for Phase 12 Network Center Services."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Set custom test db path
        NetworkDatabase._db_path = Path(self.temp_dir) / "test_network.db"
        NetworkDatabase.init_db()

    def tearDown(self):
        NetworkDatabase._db_path = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_network_models(self):
        """Test typing and serialization of network dataclasses."""
        adapter = NetworkAdapterInfo(
            name="Wi-Fi",
            description="Intel Wi-Fi 6 AX201",
            mac_address="00-11-22-33-44-55",
            ipv4_address="192.168.1.50",
            ipv4_subnet="255.255.255.0",
            ipv4_gateway="192.168.1.1",
            link_speed_mbps=866,
            status="متصل",
            is_wireless=True
        )
        self.assertEqual(adapter.name, "Wi-Fi")
        self.assertTrue(adapter.is_wireless)
        self.assertEqual(adapter.ipv4_gateway, "192.168.1.1")

        st = SpeedTestResult(
            download_mbps=120.5,
            upload_mbps=45.2,
            ping_ms=18.4,
            jitter_ms=2.1,
            packet_loss_percent=0.0
        )
        self.assertEqual(st.download_mbps, 120.5)
        self.assertEqual(st.upload_mbps, 45.2)
        self.assertEqual(st.download_mbyte_s, 15.06)

    def test_network_db_speedtest_and_events(self):
        """Test persisting and fetching speed tests and network snapshots."""
        st = SpeedTestResult(
            download_mbps=95.4,
            upload_mbps=30.0,
            ping_ms=15.0,
            jitter_ms=1.5,
            packet_loss_percent=0.0,
            provider_name="Cloudflare Edge"
        )
        row_id = NetworkDatabase.save_speed_test(st)
        self.assertGreater(row_id, 0)
        history = NetworkDatabase.get_recent_speed_tests(limit=10)
        self.assertEqual(len(history), 1)
        self.assertAlmostEqual(history[0].download_mbps, 95.4, places=1)

        # Snapshot test
        snap_id = NetworkDatabase.save_snapshot("test_snap", {"ip": "192.168.1.50"})
        self.assertGreater(snap_id, 0)

        # Outage test
        outage_id = NetworkDatabase.log_outage_start("Cable disconnected")
        self.assertGreater(outage_id, 0)
        NetworkDatabase.log_outage_end(outage_id)
        outages = NetworkDatabase.get_outages(limit=5)
        self.assertEqual(len(outages), 1)
        self.assertEqual(outages[0]["reason"], "Cable disconnected")

    def test_network_info_summary(self):
        """Test getting active connection summary."""
        summary = NetworkInfoService.get_active_connection_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn("connection_type", summary)
        self.assertIn("internet_status", summary)
        self.assertIn("dns_servers", summary)

    def test_speedtest_helpers(self):
        """Test byte/sec to MB/s and file transfer estimator."""
        st = SpeedTestResult(
            download_mbps=100.0,
            upload_mbps=20.0,
            ping_ms=15.0,
            jitter_ms=2.0,
            packet_loss_percent=0.0
        )
        self.assertAlmostEqual(st.download_mbyte_s, 12.5, places=2)

        est = st.estimate_download_time_str(gigabytes=1.0)
        self.assertIsInstance(est, str)
        self.assertGreater(len(est), 0)

    def test_doctor_diagnostics(self):
        """Test Doctor sequential diagnosis steps structure."""
        report = NetworkDoctorService.run_full_diagnosis()
        self.assertIsInstance(report, DoctorDiagnosticReport)
        self.assertIsInstance(report.stages, list)
        self.assertGreaterEqual(len(report.stages), 1)
        self.assertLessEqual(len(report.stages), 5)
        self.assertIn(report.stages[0].id, ["adapter", "ip", "gateway", "dns", "https"])
        self.assertIsInstance(report.root_cause_ar, str)
        self.assertGreater(len(report.root_cause_ar), 0)

    def test_wifi_service_helpers(self):
        """Test Wi-Fi channel analyzer logic."""
        nets = [
            NearbyWifiNetwork(ssid="HomeNet_2G", bssid="AA:BB:CC:11:22:33", signal_percent=90, channel=1, band_ghz="2.4 GHz", security="WPA2", radio_type="802.11n"),
            NearbyWifiNetwork(ssid="Neighbor1", bssid="AA:BB:CC:11:22:34", signal_percent=70, channel=1, band_ghz="2.4 GHz", security="WPA2", radio_type="802.11n"),
            NearbyWifiNetwork(ssid="Neighbor2", bssid="AA:BB:CC:11:22:35", signal_percent=50, channel=6, band_ghz="2.4 GHz", security="WPA2", radio_type="802.11n"),
        ]
        congestion = WifiService.analyze_channels(nets)
        self.assertIn("channels_24", congestion)
        self.assertIn("channels_5", congestion)
        self.assertEqual(congestion["channels_24"].get(1), 2)
        self.assertEqual(congestion["channels_24"].get(6), 1)

    def test_lan_discovery_helpers(self):
        """Test MAC vendor matching and local router launcher."""
        vendor_apple = LanDiscoveryService.get_mac_vendor("F0:18:98:12:34:56")
        self.assertIn("Apple", vendor_apple)

        vendor_intel = LanDiscoveryService.get_mac_vendor("00:1E:67:44:55:66")
        self.assertIn("Intel", vendor_intel)

        # Router launcher test
        self.assertTrue(callable(LanDiscoveryService.open_router_page))

    def test_connection_service(self):
        """Test active connections gathering."""
        conns = ConnectionService.get_active_connections()
        self.assertIsInstance(conns, list)
        if conns:
            first = conns[0]
            self.assertTrue(hasattr(first, "pid"))
            self.assertTrue(hasattr(first, "process_name"))
            self.assertTrue(hasattr(first, "local_port"))

        # Check local port helper
        is_avail, msg = ConnectionService.test_local_port_availability(59999)
        self.assertIsInstance(is_avail, bool)
        self.assertIsInstance(msg, str)

    def test_dns_service(self):
        """Test DNS benchmark servers list."""
        self.assertGreater(len(POPULAR_DNS_SERVERS), 0)
        names = [s["name"] for s in POPULAR_DNS_SERVERS]
        self.assertIn("Cloudflare", names)
        self.assertIn("Google DNS", names)

    def test_pure_qr_generator(self):
        """Test pure-Python QR matrix generator without external dependencies."""
        matrix = _generate_qr_svg_or_matrix("http://192.168.1.5:8080/sinax_share")
        self.assertIsInstance(matrix, list)
        self.assertGreater(len(matrix), 10)
        self.assertEqual(len(matrix), len(matrix[0]))

    def test_network_tools_and_report(self):
        """Test diagnostic ports and support report generation."""
        self.assertGreater(len(COMMON_DIAGNOSTIC_PORTS), 3)

        # Support report without privacy mode
        rep_full = NetworkToolsService.generate_support_report(privacy_mode=False)
        self.assertIn("system", rep_full)
        self.assertIn("public_ip", rep_full)
        self.assertFalse(rep_full["privacy_mode"])

        # Support report with privacy mode
        rep_priv = NetworkToolsService.generate_support_report(privacy_mode=True)
        self.assertTrue(rep_priv["privacy_mode"])

        txt = NetworkToolsService.export_report_to_text(rep_priv)
        self.assertIn("تقرير الدعم الفني للشبكة", txt)

    def test_adapter_service(self):
        """Test firewall status and proxy info."""
        fw = AdapterService.get_firewall_status()
        self.assertIsInstance(fw, dict)
        self.assertIn("Domain", fw)
        self.assertIn("Private", fw)
        self.assertIn("Public", fw)

        proxy = AdapterService.get_proxy_info()
        self.assertIsInstance(proxy, dict)
        self.assertIn("enabled", proxy)
        self.assertIn("server", proxy)


if __name__ == "__main__":
    unittest.main()
