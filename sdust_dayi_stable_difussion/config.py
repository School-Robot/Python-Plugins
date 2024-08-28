API_KEY = ""
API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
DEFAULT_NEG_PROMPT = "(nsfw:1.5), nude, naked, sex, porn, erotic, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, (outdoor:1.6), manboobs, backlight, (ugly:1.331), (duplicate:1.331), (morbid:1.21), (mutilated:1.21), (tranny:1.331), mutated hands, (poorly drawn hands:1.331), blurry, (bad anatomy:1.21), (bad proportions:1.331), extra limbs, (disfigured:1.331), (more than 2 nipples:1.331), (missing arms:1.331), (extra legs:1.331), (fused fingers:1.61051), (too many fingers:1.61051), (unclear eyes:1.331), bad hands, missing fingers, extra digit, (futa:1.1), bad body, NG_DeepNegative_V1_75T, badhandv4, EasyNegative"

import os,configparser
def config_init(dir):
  config_file_name = 'sd_config.ini'
  config_path = os.path.join(dir, config_file_name)
  config = configparser.ConfigParser()
  if not os.path.exists(config_path):
    my_api_key = "sk-"
    config['StableDiffusion'] = {
        "api_key": my_api_key,
        "api_url": "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
        "DEFAULT_NEG_PROMPT":DEFAULT_NEG_PROMPT
    }
    with open(config_path, 'w') as configfile:
      config.write(configfile)
  else:
    config.read(config_path)
    api_key = config.get("StableDiffusion", "api_key", fallback="")
  return config