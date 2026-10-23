"""Create deterministic raster branding from the approved project design reference."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
NAVY = (7, 31, 73, 255)
BLUE = (26, 126, 220, 255)
CYAN = (27, 207, 238, 255)
ORANGE = (255, 166, 34, 255)
WHITE = (255, 255, 255, 255)


def icon(size: int, dark: bool = False) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    margin = size * .04; d.rounded_rectangle((margin, margin, size-margin, size-margin), radius=size*.18, fill=NAVY if dark else (13, 112, 205, 255))
    cx = size*.5; bell_top = size*.18; bell_bottom = size*.63; w=size*.34
    d.ellipse((cx-w*.55,bell_top-w*.18,cx+w*.55,bell_top+w*.9), fill=(113, 207, 255, 255))
    d.rounded_rectangle((cx-w,bell_top+w*.25,cx+w,bell_bottom), radius=size*.09, fill=(76, 177, 239, 255))
    d.pieslice((cx-w*1.22,bell_bottom-size*.045,cx+w*1.22,bell_bottom+size*.13), 0, 180, fill=(224, 247, 255, 255))
    d.ellipse((cx-size*.055,bell_bottom+size*.03,cx+size*.055,bell_bottom+size*.13), fill=ORANGE)
    for radius, width in ((.31,.035),(.39,.026)):
        d.arc((cx-size*radius, size*.18, cx+size*radius, size*.76), 120, 240, fill=CYAN, width=max(2,int(size*width)))
        d.arc((cx-size*radius, size*.18, cx+size*radius, size*.76), -60, 60, fill=CYAN, width=max(2,int(size*width)))
    y=size*.79; nodes=[size*.25,size*.5,size*.75]
    for x in nodes: d.line((cx,size*.64,x,y),fill=CYAN,width=max(2,int(size*.025)))
    for x, color in zip(nodes,(BLUE,CYAN,(71,72,220,255))):
        d.ellipse((x-size*.105,y-size*.105,x+size*.105,y+size*.105),fill=color,outline=WHITE,width=max(2,int(size*.012)))
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',max(10,int(size*.075)))
    for x, glyph in zip(nodes,("⌂","▯","▣")): d.text((x,y),glyph,font=font,fill=WHITE,anchor='mm')
    return im


def main() -> None:
    brand=ROOT/'custom_components/smart_notifications/brand'; assets=ROOT/'assets'; brand.mkdir(parents=True,exist_ok=True)
    icon(256).save(brand/'icon.png'); icon(512).save(brand/'icon@2x.png')
    for width, path in ((1200,brand/'logo.png'),(2400,brand/'logo@2x.png')):
        height=300 if width==1200 else 600; im=Image.new('RGBA',(width,height),(255,255,255,0)); im.alpha_composite(icon(int(height*.88)),(int(height*.04),int(height*.06)))
        d=ImageDraw.Draw(im); scale=height/300; bold=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',int(58*scale)); sub=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',int(24*scale)); x=int(height*.98)
        d.text((x,int(height*.28)), 'Smart', font=bold, fill=NAVY); d.text((x,int(height*.48)), 'Notifications', font=bold, fill=(24,104,210,255)); d.text((x,int(height*.75)), 'FÜR HOME ASSISTANT', font=sub, fill=(92,104,123,255)); im.save(path)
    social=Image.new('RGBA',(1280,640),(5,25,62,255)); social.alpha_composite(icon(360),(70,140)); d=ImageDraw.Draw(social); d.text((500,190),'Smart Notifications',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',62),fill=WHITE); d.text((505,280),'Zentrale Benachrichtigungen für Home Assistant',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',28),fill=CYAN); social.save(assets/'github-social-preview.png')


if __name__ == '__main__': main()
