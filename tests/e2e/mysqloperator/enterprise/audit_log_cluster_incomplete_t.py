# Copyright (c) 2022, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl/
#

import unittest
from e2e.mysqloperator.enterprise.audit_log_base import AuditLogBase
from setup.config import g_ts_cfg
from utils import auxutil
from utils import mutil

# test the audit log on the 3-instance cluster, with plugin installed on two
# instances (the primary and one secondary)
@unittest.skipIf(g_ts_cfg.enterprise_skip, "Enterprise test cases are skipped")
class AuditLogClusterIncomplete(AuditLogBase):
    add_data_timestamp = None
    test_table = "cluster0"
    instance_primary = "mycluster-0"

    def test_0_create(self):
        self.create_cluster()


    def test_1_init(self):
        self.install_plugin_on_secondary("mycluster-1")
        self.install_plugin_on_primary(self.instance_primary)
        self.set_default_filter(self.instance_primary)


    def test_2_prepare_data(self):
        self.__class__.add_data_timestamp = auxutil.utctime()

        with mutil.MySQLPodSession(self.ns, self.instance_primary, self.user, self.password) as s:
            s.exec_sql("CREATE SCHEMA audit_foo")
            s.exec_sql(f"CREATE TABLE audit_foo.{self.test_table} (id INT NOT NULL)")

        with mutil.MySQLPodSession(self.ns, "mycluster-1", self.user, self.password) as s:
            res = s.query_sql("SHOW TABLES").fetch_all()
            self.assertIsNotNone(res)

        with mutil.MySQLPodSession(self.ns, "mycluster-2", self.user, self.password) as s:
            res = s.query_sql("SHOW DATABASES").fetch_all()
            self.assertIsNotNone(res)


    def test_3_verify_log(self):
        self.assertTrue(self.does_log_exist(self.instance_primary))
        self.assertTrue(self.does_log_exist("mycluster-1"))
        self.assertFalse(self.does_log_exist("mycluster-2"))

        self.assertTrue(self.has_default_filter_set("mycluster-0"))
        log_data_0 = self.get_log_data(self.instance_primary, self.add_data_timestamp)
        self.assertIn("CREATE SCHEMA audit_foo", log_data_0)
        self.assertIn(f"CREATE TABLE audit_foo.{self.test_table} (id INT NOT NULL)", log_data_0)
        self.assertNotIn("SHOW TABLES", log_data_0)
        self.assertNotIn("SHOW DATABASES", log_data_0)

        self.assertTrue(self.has_default_filter_set("mycluster-1"))
        log_data_1 = self.get_log_data("mycluster-1", self.add_data_timestamp)
        self.assertNotIn("CREATE SCHEMA audit_foo", log_data_1)
        self.assertNotIn(f"CREATE TABLE audit_foo.{self.test_table} (id INT NOT NULL)", log_data_1)
        self.assertIn("SHOW TABLES", log_data_1)
        self.assertNotIn("SHOW DATABASES", log_data_1)

        self.assertTrue(self.has_default_filter_set("mycluster-2"))


    def test_9_destroy(self):
        self.destroy_cluster()
