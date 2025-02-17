from .const import (
    DOMAIN,
    CONF_MEMORY_PATHS,
    CONG_MEMORY_IMAGES_ENCODED,
    CONF_MEMORY_STRINGS,
    CONF_SYSTEM_PROMPT
)
import base64
import io
from PIL import Image
import logging

_LOGGER = logging.getLogger(__name__)


class Memory:
    def __init__(self, hass):
        self.hass = hass
        self.entry = self._find_memory_entry()
        self.system_prompt = self.entry.data.get(CONF_SYSTEM_PROMPT, "")
        self.memory_strings = self.entry.data.get(CONF_MEMORY_STRINGS, [])
        self.memory_paths = self.entry.data.get(CONF_MEMORY_PATHS, [])
        self.memory_images = self.entry.data.get(
            CONG_MEMORY_IMAGES_ENCODED, [])

    def get_memory_strings(self):
        return self.memory_strings

    def _get_memory_images(self, type="OpenAI"):
        content = []
        if type == "OpenAI":
            content.append(
                {"type": "text", "text": "The following images along with descriptions serve as reference. They are not to be mentioned in the response."})
            for image in self.memory_images:
                tag = self.memory_strings[self.memory_images.index(image)]

                content.append(
                    {"type": "text", "text": tag + ":"})
                content.append({"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{image}"}})

        elif type == "Anthropic":
            content.append(
                {"type": "text", "text": "The following images along with descriptions serve as reference. They are not to be mentioned in the response."})
            for image in self.memory_images:
                tag = self.memory_strings[self.memory_images.index(image)]

                content.append(
                    {"type": "text", "text": tag + ":"})
                content.append({"type": "image", "source": {
                    "type": "base64", "media_type": "image/jpeg", "data": f"{image}"}})
        elif type == "Google":
            content.append(
                {"type": "text", "text": "The following images along with descriptions serve as reference. They are not to be mentioned in the response."})
            for image in self.memory_images:
                tag = self.memory_strings[self.memory_images.index(image)]

                content.append(
                    {"type": "text", "text": tag + ":"})
                content.append({"type": "image", "source": {
                    "type": "base64", "data": f"{image}"}})
        elif type == "AWS":
            content.append(
                {"type": "text", "text": "The following images along with descriptions serve as reference. They are not to be mentioned in the response."})
            for image in self.memory_images:
                tag = self.memory_strings[self.memory_images.index(image)]

                content.append(
                    {"text": tag + ":"})
                content.append({"image": {
                    "format": "jpeg", "source": {"bytes": image}}})
        else:
            return None

        return content

    def get_system_prompt(self):
        return "System prompt: " + self.system_prompt

    def _find_memory_entry(self):
        memory_entry = None
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            # Check if the config entry is empty
            if entry.data["provider"] == "Memory":
                memory_entry = entry
                break

        if memory_entry is None:
            _LOGGER.error("Memory entry not set up")
            return None

        return memory_entry

    async def _encode_images(self, image_paths):
        """Encode images as base64"""
        encoded_images = []

        for image_path in image_paths:
            img = await self.hass.loop.run_in_executor(None, Image.open, image_path)
            with img:
                # calculate new height and width based on aspect ratio
                width, height = img.size
                aspect_ratio = width / height
                if aspect_ratio > 1:
                    new_width = 512
                    new_height = int(512 / aspect_ratio)
                else:
                    new_height = 512
                    new_width = int(512 * aspect_ratio)
                img = img.resize((new_width, new_height))

                # Encode the image to base64
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                base64_image = base64.b64encode(
                    img_byte_arr.getvalue()).decode('utf-8')
                encoded_images.append(base64_image)

        return encoded_images

    async def _update_memory(self):
        """Manage encoded images"""

        # check if len(memory_paths) != len(memory_images)
        if len(self.memory_paths) != len(self.memory_images):
            self.memory_images = await self._encode_images(self.memory_paths)

            # update memory with new images
            memory = self.entry.data.copy()
            memory['images'] = self.memory_images
            self.hass.config_entries.async_update_entry(
                self.entry, data=memory)

    def __str__(self):
        return f"Memory:({self.memory_strings}, {self.memory_paths})"
