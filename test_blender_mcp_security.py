import importlib
import os
import sys
import types
import unittest
from unittest import mock


def _install_blender_stubs():
    props_module = types.ModuleType("bpy.props")
    props_module.IntProperty = lambda **kwargs: None
    props_module.BoolProperty = lambda **kwargs: None
    props_module.EnumProperty = lambda **kwargs: None
    props_module.StringProperty = lambda **kwargs: None
    props_module.FloatProperty = lambda **kwargs: None

    class Scene:
        blendermcp_use_polyhaven = False
        blendermcp_use_hyper3d = False
        blendermcp_use_sketchfab = False
        blendermcp_use_hunyuan3d = False

    bpy_module = types.ModuleType("bpy")
    bpy_module.props = props_module
    bpy_module.types = types.SimpleNamespace(
        AddonPreferences=object,
        Operator=object,
        Panel=object,
        Scene=Scene,
    )
    bpy_module.context = types.SimpleNamespace(
        scene=Scene(),
        preferences=types.SimpleNamespace(addons={}),
    )
    bpy_module.app = types.SimpleNamespace(
        version=(4, 0, 0),
        timers=types.SimpleNamespace(register=lambda *args, **kwargs: None),
    )
    bpy_module.utils = types.SimpleNamespace(
        register_class=lambda cls: None,
        unregister_class=lambda cls: None,
    )
    bpy_module.data = types.SimpleNamespace()
    bpy_module.ops = types.SimpleNamespace()

    mathutils_module = types.ModuleType("mathutils")
    mathutils_module.Vector = lambda value: value

    sys.modules["bpy"] = bpy_module
    sys.modules["bpy.props"] = props_module
    sys.modules["mathutils"] = mathutils_module


class BlenderMCPServerSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_blender_stubs()
        cls.addon = importlib.import_module("blender_mcp_addon")

    def test_execute_code_is_denied_by_default_and_not_invoked(self):
        server = self.addon.BlenderMCPServer(allow_unsafe_execute_code=False)
        server.execute_code = mock.Mock(return_value={"executed": True})

        response = server.execute_command({
            "type": "execute_code",
            "params": {"code": "open('/tmp/blender_mcp_pwned', 'w').write('x')"},
        })

        self.assertEqual(response["status"], "error")
        self.assertIn("execute_code is disabled", response["message"])
        server.execute_code.assert_not_called()

    def test_execute_code_requires_explicit_unsafe_opt_in(self):
        with mock.patch.dict(
            os.environ,
            {
                self.addon.UNSAFE_EXECUTE_CODE_ENV: "1",
                self.addon.EXECUTE_CODE_TOKEN_ENV: "secret",
            },
        ):
            server = self.addon.BlenderMCPServer()
        server.execute_code = mock.Mock(return_value={"executed": True, "result": ""})

        response = server.execute_command({
            "type": "execute_code",
            "token": "secret",
            "params": {"code": "print('allowed')"},
        })

        self.assertEqual(response["status"], "success")
        server.execute_code.assert_called_once_with(code="print('allowed')")

    def test_execute_code_requires_token_when_unsafe_mode_is_enabled(self):
        server = self.addon.BlenderMCPServer(
            allow_unsafe_execute_code=True,
            execute_code_token="secret",
        )
        server.execute_code = mock.Mock(return_value={"executed": True})

        missing_response = server.execute_command({
            "type": "execute_code",
            "params": {"code": "print('denied')"},
        })
        invalid_response = server.execute_command({
            "type": "execute_code",
            "token": "wrong",
            "params": {"code": "print('denied')"},
        })

        self.assertEqual(missing_response["status"], "error")
        self.assertIn("requires a valid token", missing_response["message"])
        self.assertEqual(invalid_response["status"], "error")
        self.assertIn("requires a valid token", invalid_response["message"])
        server.execute_code.assert_not_called()

    def test_execute_code_requires_configured_token_when_unsafe_mode_is_enabled(self):
        server = self.addon.BlenderMCPServer(allow_unsafe_execute_code=True)
        server.execute_code = mock.Mock(return_value={"executed": True})

        response = server.execute_command({
            "type": "execute_code",
            "token": "secret",
            "params": {"code": "print('denied')"},
        })

        self.assertEqual(response["status"], "error")
        self.assertIn("requires a valid token", response["message"])
        server.execute_code.assert_not_called()


if __name__ == "__main__":
    unittest.main()
