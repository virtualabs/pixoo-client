"""
Pixoo 
"""

import socket
from time import sleep
from PIL import Image
from binascii import unhexlify, hexlify
from math import log10, ceil

class Pixoo(object):

  CMD_SET_SYSTEM_BRIGHTNESS = 0x74
  CMD_SPP_SET_USER_GIF = 0xb1
  CMD_DRAWING_ENCODE_PIC = 0x5b

  BOX_MODE_CLOCK=0
  BOX_MODE_TEMP=1
  BOX_MODE_COLOR=2
  BOX_MODE_SPECIAL=3

  instance = None

  def __init__(self, mac_address):
    """
    Constructor
    """
    self.mac_address = mac_address
    self.btsock = None


  @staticmethod
  def get():
    if Pixoo.instance is None:
      Pixoo.instance = Pixoo(Pixoo.BDADDR)
      Pixoo.instance.connect()
    return Pixoo.instance

  def connect(self):
    """
    Connect to SPP.
    """
    self.btsock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    self.btsock.connect((self.mac_address, 1))


  def __spp_frame_checksum(self, args):
    """
    Compute frame checksum
    """
    return sum(args[1:])&0xffff


  def __spp_frame_encode(self, cmd, args):
    """
    Encode frame for given command and arguments (list).
    """
    payload_size = len(args) + 3

    # create our header
    frame_header = [1, payload_size & 0xff, (payload_size >> 8) & 0xff, cmd]

    # concatenate our args (byte array)
    frame_buffer = frame_header + args

    # compute checksum (first byte excluded)
    cs = self.__spp_frame_checksum(frame_buffer)

    # create our suffix (including checksum)
    frame_suffix = [cs&0xff, (cs>>8)&0xff, 2]

    # return output buffer
    return frame_buffer+frame_suffix


  def send(self, cmd, args):
    """
    Send data to SPP.
    """
    spp_frame = self.__spp_frame_encode(cmd, args)
    if self.btsock is not None:
      nb_sent = self.btsock.send(bytes(spp_frame))


  def set_system_brightness(self, brightness):
    """
    Set system brightness.
    """
    self.send(Pixoo.CMD_SET_SYSTEM_BRIGHTNESS, [brightness&0xff])


  def set_box_mode(self, boxmode, visual=0, mode=0):
    """
    Set box mode.
    """
    self.send(0x45, [boxmode&0xff, visual&0xff, mode&0xff])


  def set_color(self, r,g,b):
    """
    Set color.
    """
    self.send(0x6f, [r&0xff, g&0xff, b&0xff])

  def encode_image(self, filepath):
    img = Image.open(filepath)
    return self.encode_raw_image(img)

  def encode_raw_image(self, img):
    """
    Encode a 16x16 image.
    """
    # ensure image is 16x16
    w,h = img.size
    if w == h:
      # resize if image is too big
      if w > 16:
        img = img.resize((16,16))

      # create palette and pixel array
      pixels = []
      palette = []
      for y in range(16):
        for x in range(16):
          pix = img.getpixel((x,y))
          
          if len(pix) == 4:
            r,g,b,a = pix
          elif len(pix) == 3:
            r,g,b = pix
          if (r,g,b) not in palette:
            palette.append((r,g,b))
            idx = len(palette)-1
          else:
            idx = palette.index((r,g,b))
          pixels.append(idx)

      # encode pixels
      bitwidth = ceil(log10(len(palette))/log10(2))
      nbytes = ceil((256*bitwidth)/8.)
      encoded_pixels = [0]*nbytes

      encoded_pixels = []
      encoded_byte = ''
      for i in pixels:
        encoded_byte = bin(i)[2:].rjust(bitwidth, '0') + encoded_byte
        if len(encoded_byte) >= 8:
            encoded_pixels.append(encoded_byte[-8:])
            encoded_byte = encoded_byte[:-8]
      encoded_data = [int(c, 2) for c in encoded_pixels]
      encoded_palette = []
      for r,g,b in palette:
        encoded_palette += [r,g,b]
      return (len(palette), encoded_palette, encoded_data)
    else:
      print('[!] Image must be square.')

  def draw_gif(self, filepath, speed=100):
    """
    Parse Gif file and draw as animation.
    """
    # encode frames
    frames = []
    timecode = 0
    anim_gif = Image.open(filepath)
    for n in range(anim_gif.n_frames):
      anim_gif.seek(n)
      nb_colors, palette, pixel_data = self.encode_raw_image(anim_gif.convert(mode='RGB'))
      frame_size = 7 + len(pixel_data) + len(palette)
      frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, timecode&0xff, (timecode>>8)&0xff, 0, nb_colors]
      frame = frame_header + palette + pixel_data
      frames += frame
      timecode += speed

    # send animation
    nchunks = ceil(len(frames)/200.)
    total_size = len(frames)
    for i in range(nchunks):
      chunk = [total_size&0xff, (total_size>>8)&0xff, i]
      self.send(0x49, chunk+frames[i*200:(i+1)*200])
   

  def draw_anim(self, filepaths, speed=100):
    timecode=0

    # encode frames
    frames = []
    n=0
    for filepath in filepaths:
      nb_colors, palette, pixel_data = self.encode_image(filepath)
      frame_size = 7 + len(pixel_data) + len(palette)
      frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, timecode&0xff, (timecode>>8)&0xff, 0, nb_colors]
      frame = frame_header + palette + pixel_data
      frames += frame
      timecode += speed
      n += 1
    
    # send animation
    nchunks = ceil(len(frames)/200.)
    total_size = len(frames)
    for i in range(nchunks):
      chunk = [total_size&0xff, (total_size>>8)&0xff, i]
      self.send(0x49, chunk+frames[i*200:(i+1)*200])


  def draw_pic(self, filepath):
    """
    Draw encoded picture.
    """
    nb_colors, palette, pixel_data = self.encode_image(filepath)
    frame_size = 7 + len(pixel_data) + len(palette)
    frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, 0, 0, 0, nb_colors]
    frame = frame_header + palette + pixel_data
    prefix = [0x0, 0x0A,0x0A,0x04]
    self.send(0x44, prefix+frame)


class PixooMax(Pixoo):
  """
  PixooMax class, derives from Pixoo but does not support animation yet.
  """
  
  def __init__(self, mac_address):
    super().__init__(mac_address)

  def draw_pic(self, filepath):
    """
    Draw encoded picture.
    """
    nb_colors, palette, pixel_data = self.encode_image(filepath)
    frame_size = 8 + len(pixel_data) + len(palette)
    frame_header = [0xAA, frame_size&0xff, (frame_size>>8)&0xff, 0, 0, 3, nb_colors&0xff, (nb_colors&0xff00)>>8]
    frame = frame_header + palette + pixel_data
    prefix = [0x0, 0x0A,0x0A,0x04]
    self.send(0x44, prefix+frame)

  def draw_gif(self, filepath, speed=100):
    raise 'NotYetImplemented'

  def draw_anim(self, filepaths, speed=100):
    raise 'NotYetImplemented'

  def encode_image(self, filepath):
    img = Image.open(filepath)
    return self.encode_raw_image(img)

  def encode_raw_image(self, img):
    """
    Encode a 32x32 image.
    """
    # ensure image is 32x32
    w,h = img.size
    if w == h:
      # resize if image is too big
      if w > 32:
        img = img.resize((32,32))

      # create palette and pixel array
      pixels = []
      palette = []
      for y in range(32):
        for x in range(32):
          pix = img.getpixel((x,y))
          
          if len(pix) == 4:
            r,g,b,a = pix
          elif len(pix) == 3:
            r,g,b = pix
          if (r,g,b) not in palette:
            palette.append((r,g,b))
            idx = len(palette)-1
          else:
            idx = palette.index((r,g,b))
          pixels.append(idx)

      # encode pixels
      bitwidth = ceil(log10(len(palette))/log10(2))
      nbytes = ceil((256*bitwidth)/8.)
      encoded_pixels = [0]*nbytes

      encoded_pixels = []
      encoded_byte = ''
      for i in pixels:
        encoded_byte = bin(i)[2:].rjust(bitwidth, '0') + encoded_byte
        if len(encoded_byte) >= 8:
            encoded_pixels.append(encoded_byte[-8:])
            encoded_byte = encoded_byte[:-8]
      encoded_data = [int(c, 2) for c in encoded_pixels]
      encoded_palette = []
      for r,g,b in palette:
        encoded_palette += [r,g,b]
      return (len(palette), encoded_palette, encoded_data)
    else:
      print('[!] Image must be square.')

if __name__ == '__main__':
    pixoo = PixooMax('11:75:58:51:AC:4D')
    pixoo.connect()

    # mandatory to wait at least 1 second
    sleep(1)

    pixoo.draw_pic('sonic.png')