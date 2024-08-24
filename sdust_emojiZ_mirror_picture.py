"""
图片镜像
"""
import os.path
import os
import requests
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageDraw, ImageSequence
import numpy as np

plugin_name = "mirror_picture"
plugin_id = "sdust.emojiZ.mirror_picture"
plugin_version = "1.0.0"
plugin_author = "Z"
plugin_desc = "图片镜像"


class Plugin(object):
    plugin_methods = {'register': {'priority': 30000, 'func': 'register', 'desc': '注册插件'},
                      'enable': {'priority': 30000, 'func': 'enable', 'desc': '启用插件'},
                      'disable': {'priority': 30000, 'func': 'disable', 'desc': '禁用插件'},
                      'unregister': {'priority': 30000, 'func': 'unregister', 'desc': '卸载插件'},
                      'group_message': {'priority': 30000, 'func': 'group_message', 'desc': '群消息处理'}}
    plugin_commands = {}
    plugin_auths = {'send_group_msg', 'get_msg', 'get_image'}
    auth = ''
    log = None
    status = None
    bot = None
    util = None
    dir = None

    def register(self, logger, util, bot, dir):
        self.log = logger
        self.bot = bot
        self.util = util
        self.dir = dir
        self.operations = {
            '旋转90度': lambda img: img.rotate(270, expand=True),  # 90度顺时针
            '旋转180度': lambda img: img.rotate(180, expand=True),
            '旋转270度': lambda img: img.rotate(90, expand=True),   # 270度顺时针
            '锐化': lambda img: img.filter(ImageFilter.SHARPEN),
            '黑白': lambda img: img.convert('L'),
            '增加亮度': lambda img: ImageEnhance.Brightness(img).enhance(1.5),  # 增加亮度
            '减少亮度': lambda img: ImageEnhance.Brightness(img).enhance(0.5),  # 减少亮度
            '增加对比度': lambda img: ImageEnhance.Contrast(img).enhance(1.5),  # 增加对比度
            '减少对比度': lambda img: ImageEnhance.Contrast(img).enhance(0.5),  # 减少对比度
            '边缘检测': lambda img: img.filter(ImageFilter.FIND_EDGES),
            '浮雕效果': lambda img: img.filter(ImageFilter.EMBOSS),
            '反色': lambda img: ImageOps.invert(img.convert('RGB')),
            '降噪': lambda img: img.filter(ImageFilter.MedianFilter(size=3)),  # 降噪
            '添加噪点': lambda img: self.add_noise(img),  # 添加噪点
            '老照片': lambda img: self.apply_old_photo_effect(img),  # 老照片效果
            '马赛克': lambda img: self.apply_mosaic(img, 10),  # 马赛克效果
            '增加饱和度': lambda img: ImageEnhance.Color(img).enhance(1.5),  # 增加饱和度
            '减少饱和度': lambda img: ImageEnhance.Color(img).enhance(0.5),  # 减少饱和度
            '水平翻转': lambda img: img.transpose(Image.FLIP_LEFT_RIGHT),
            '垂直翻转': lambda img: img.transpose(Image.FLIP_TOP_BOTTOM),
            '素描效果': lambda img: self.apply_sketch_effect(img),  # 素描效果
            '水彩效果': lambda img: self.apply_watercolor_effect(img),  # 水彩效果
            '油画效果': lambda img: self.apply_oil_paint_effect(img),  # 油画效果
            '添加边框': lambda img: self.add_border(img, 10),  # 添加边框
            '高斯模糊': lambda img: img.filter(ImageFilter.GaussianBlur(5)),  # 高斯模糊
            '波浪效果': lambda img: self.apply_wave_effect(img),  # 波浪效果
            '漩涡效果': lambda img: self.apply_whirlpool_effect(img),  # 漩涡效果
            '增加色温': lambda img: self.increase_color_temperature(img),  # 增加色温
            '减少色温': lambda img: self.decrease_color_temperature(img),  # 减少色温
            '镜像': lambda img: img.transpose(Image.FLIP_LEFT_RIGHT),
        }
        self.log.info("Plugin register")

    def enable(self, auth):
        self.auth = auth
        self.log.info("Plugin enable")

    def disable(self):
        self.log.info("Plugin disable")

    def unregister(self):
        self.log.info("Plugin unregister")

    def group_message(self, time, self_id, sub_type, message_id, group_id, user_id, anonymous, message, raw_message,
                      font, sender):
        if raw_message.startswith("#可用操作"):
            operations_list = ', '.join(self.operations.keys())
            self.util.send_group_msg(self.auth, group_id, f"请回复一个图片，回复以下内容即可处理图片:\n{operations_list}")
        if raw_message.startswith("[CQ:reply,id="):
            operation_key = None
            for key in self.operations.keys():
                if key in raw_message:
                    operation_key = key
                    break
            if operation_key is None:
                return True
            target_message_id = raw_message.replace("[CQ:reply,id=", "")[:-3]
            flag, data = self.util.get_msg(self.auth, target_message_id)
            if flag:
                target_message = data['message'][0]
                if target_message['type'] == "image":
                    image_url = target_message['data']['url']
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        temp_dir = os.path.join(self.dir, 'tmp')
                        os.makedirs(temp_dir, exist_ok=True)
                        image_name = target_message['data']['file']
                        save_path = os.path.join(temp_dir, image_name)
                        with open(save_path, 'wb') as file:
                            file.write(response.content)
                        self.log.info(f"图片已保存到: {save_path}")
                        final_path = self.transform_image(save_path, operation_key)
                        send_by_cq = self.util.cq_image(file=final_path, type="")
                        success, _ = self.util.send_group_msg(self.auth, group_id, send_by_cq)
                        if success:
                            os.remove(save_path)
                            os.remove(final_path)
                            self.log.debug(f"已移除图片{save_path}及其转换图片")
                            return True
                        else:
                            self.log.error("图片发送超时")
                            return False
                    else:
                        self.log.error(f"下载失败，状态码: {response.status_code}")
                        return False

                else:
                    return False
            else:
                self.util.send_group_msg(self.auth, group_id, "发送错误,请重试")
                return False


    def transform_image(self, input_path, operation='翻转'):
        with Image.open(input_path) as img:
            # 检查图像是否为 GIF 动画
            base, ext = os.path.splitext(input_path)
            output_path = base + '-' + operation + ".gif"
            if img.format == "GIF":
                frames = []
                for frame in ImageSequence.Iterator(img):
                    transformed_frame = self.apply_operation(frame.convert('RGBA'), operation)
                    frames.append(transformed_frame)
                frames[0].save(output_path, save_all=True, append_images=frames[1:], loop=0)
                return output_path
            else:
                transformed_image = self.apply_operation(img, operation)
                transformed_image.save(output_path)
                return output_path
    
    def apply_operation(self, image, operation):    
        # 检查操作是否合法
        if operation not in self.operations:
            raise ValueError("Invalid operation. Choose from the defined operations.")
        # 处理图像
        return self.operations[operation](image)
    
    # 示例的附加效果函数
    def add_noise(self, image):
        # 添加噪点
        noise = np.random.normal(0, 25, (image.size[1], image.size[0], 3)).astype(np.uint8)
        noisy_image = np.array(image) + noise
        return Image.fromarray(np.clip(noisy_image, 0, 255).astype(np.uint8))
    
    def apply_old_photo_effect(self, image):
        # 创建一个黄色遮罩
        yellow_mask = Image.new('RGBA', image.size, (255, 255, 0, 50))  # 半透明黄色
        # 将遮罩应用到原图上
        img_with_mask = Image.alpha_composite(image.convert('RGBA'), yellow_mask)

        return img_with_mask.convert('RGB')  # 转换回 RGB 模式
 
    def apply_mosaic(self, image, mosaic_size):
        # 马赛克效果
        small = image.resize((image.size[0] // mosaic_size, image.size[1] // mosaic_size), Image.NEAREST)
        return small.resize(image.size, Image.NEAREST)
    
    def apply_sketch_effect(self, image):
        # 将图像转换为灰度图
        gray_image = image.convert('L')

        # 使用边缘检测
        edge_image = gray_image.filter(ImageFilter.FIND_EDGES)

        # 将边缘图像反转
        inverted_edge_image = Image.eval(edge_image, lambda x: 255 - x)

        # 将灰度图像与边缘图像结合
        sketch_image = Image.blend(gray_image, inverted_edge_image, alpha=0.5)

        return sketch_image
 
    def apply_watercolor_effect(self, image):
        # 水彩效果（简单实现）
        return image.filter(ImageFilter.SMOOTH)
    
    def apply_oil_paint_effect(self, image):
        # 油画效果（使用 PIL 的油画滤镜）
        return image.filter(ImageFilter.ModeFilter(size=5))
    
    def add_border(self, image, border_size):
        # 添加边框
        return ImageOps.expand(image, border=border_size, fill='black')
    
    def apply_wave_effect(self, image):
        # 波浪效果
        width, height = image.size
        wave_image = Image.new("RGB", (width, height))
        for y in range(height):
            offset = int(10 * np.sin(2 * np.pi * y / 30))  # 波浪幅度和频率
            for x in range(width):
                new_x = (x + offset) % width
                wave_image.putpixel((x, y), image.getpixel((new_x, y)))
        return wave_image
    
    def apply_whirlpool_effect(self, image):
        # 漩涡效果
        width, height = image.size
        whirl_image = Image.new("RGB", (width, height))
        center_x, center_y = width // 2, height // 2
        max_radius = min(center_x, center_y)
    
        for y in range(height):
            for x in range(width):
                dx, dy = x - center_x, y - center_y
                radius = np.sqrt(dx**2 + dy**2)
                angle = np.arctan2(dy, dx) + (radius / max_radius) * np.pi / 2  # 旋转角度
                new_x = int(center_x + radius * np.cos(angle))
                new_y = int(center_y + radius * np.sin(angle))
                if 0 <= new_x < width and 0 <= new_y < height:
                    whirl_image.putpixel((x, y), image.getpixel((new_x, new_y)))
                else:
                    whirl_image.putpixel((x, y), (0, 0, 0))  # 边界外填充黑色
        return whirl_image
    
    def increase_color_temperature(self, image):
        # 增加色温
        r, g, b = image.split()
        r = r.point(lambda i: min(i * 1.1, 255))  # 增加红色通道
        return Image.merge("RGB", (r, g, b))
    
    def decrease_color_temperature(self, image):
        # 减少色温
        r, g, b = image.split()
        b = b.point(lambda i: min(i * 1.1, 255))  # 增加蓝色通道
        return Image.merge("RGB", (r, g, b))
