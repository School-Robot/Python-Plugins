import json
import os
import configparser
import requests
import base64
from io import BytesIO
from PIL import Image

def group_message_func(time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message, font, sender, util, dir,configer,logger):
    
    api_key = configer.get("StableDiffusion", "api_key", fallback="")
    api_url = configer.get("StableDiffusion", "api_url", fallback="")
    default_neg_prompt = configer.get("StableDiffusion", "DEFAULT_NEG_PROMPT", fallback="")

    API_KEY = api_key
    API_URL = api_url
    DEFAULT_NEG_PROMPT = default_neg_prompt

    prompt = raw_message[4:].strip()
    try:
        logger.info(f'[SD]正在请求API:{API_URL}')
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            },
            json={
                "text_prompts": [
                    {
                        "text": prompt
                    },
                    {
                        "text": DEFAULT_NEG_PROMPT,
                        "weight": -1
                    }
                ],
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30,
            },
        )

        if response.status_code != 200:
            logger.error("[SD]请求API出错")
            raise Exception(f"Non-200 response: {str(response.text)}")
        
        logger.info("[SD]请求API成功")

        data = response.json()
        
        for i, image in enumerate(data["artifacts"]):
            image_data = base64.b64decode(image["base64"])
            img = Image.open(BytesIO(image_data))
            
            image_path = os.path.join(dir, f"generated_image_{i}.png")
            img.save(image_path)
            
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            cq_image = f"[CQ:image,file=base64://{encoded_string}]"
            
            reply_info = util.cq_reply(message_id) + f"图片已生成，提示词：{prompt}\n{cq_image}"
            return True, reply_info
    
    except Exception as e:
        reply_info = util.cq_reply(message_id) + f"生成图片时出错：{str(e)}"
        return True, reply_info