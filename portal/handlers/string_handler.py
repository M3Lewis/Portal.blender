import json
from typing import Tuple

import bpy

from ..data_struct.camera import Camera
from ..data_struct.material import Material
from ..data_struct.mesh import Mesh


class StringHandler:
    @staticmethod
    def handle_string(payload, data_type, index, channel_name):
        """Handle generic string data for different types."""
        if payload is None:
            return

        try:
            if data_type == "Custom":
                StringHandler._handle_custom_data(payload, channel_name)
            elif data_type == "Mesh":
                StringHandler._handle_mesh_data(payload, channel_name)
            elif data_type == "Camera":
                StringHandler._handle_camera_data(payload)
        except json.JSONDecodeError:
            raise ValueError(f"Unsupported data: {payload}")

    @staticmethod
    def _handle_custom_data(payload, channel_name):
        """Write custom payload data to Blender text block."""
        text_block_name = f"{channel_name}"
        if text_block_name not in bpy.data.texts:
            bpy.data.texts.new(text_block_name)
        bpy.data.texts[text_block_name].clear()
        bpy.data.texts[text_block_name].write(payload)
        print(f"Write to text block: {text_block_name}")

    @staticmethod
    def _handle_mesh_data(payload, channel_name):
        """Handle mesh data payload."""
        message_dicts, global_metadata = StringHandler.unpack_packet(json.loads(payload))
        for i, item in enumerate(message_dicts):
            data, metadata = StringHandler.unpack_packet(item)
            mesh = Mesh.from_dict(dict=data)
            layer_path, layer_mat = StringHandler._handle_layer(metadata, channel_name)
            mesh.create_or_replace(object_name=f"obj_{i}_{channel_name}", layer_path=layer_path)

            if metadata["Material"]:
                StringHandler._apply_mesh_material(mesh, metadata["Material"])
            elif layer_mat:
                StringHandler._apply_mesh_material(mesh, layer_mat)

    @staticmethod
    def _handle_camera_data(payload):
        """Handle camera data payload."""
        camera_data = json.loads(payload)
        if not camera_data:
            raise ValueError("Camera data is empty.")
        cam = Camera.from_dict(camera_data)
        cam.sync_camera("Camera")
        cam.set_cliping(near=0.1, far=10000)

    @staticmethod
    def unpack_packet(packet: str) -> Tuple[str, str]:
        """Unpack a JSON packet into items and metadata."""
        try:
            return packet["Items"], packet["Meta"]
        except json.JSONDecodeError:
            raise ValueError(f"Unsupported packet data: {packet}")

    @staticmethod
    def _apply_mesh_material(mesh, material_data):
        material = Material.from_dict(material_data)
        material.create_or_replace(material_data.get("Name"))
        mesh.apply_material(material.name)

    @staticmethod
    def _handle_layer(data: dict, channel_name: str) -> None:
        """Handle layer path data."""
        layer_path = data.get("Layer").get("FullPath")
        if not layer_path:
            layer_path = channel_name
        else:
            layer_path = f"{channel_name}::{layer_path}"

        layer_mat = data.get("Layer").get("Material")
        return layer_path, layer_mat

    @staticmethod
    def _get_name(metadata: str) -> str:
        """Get object name from metadata."""
        if metadata is None:
            return "object"
        return metadata.get("Name", "object")