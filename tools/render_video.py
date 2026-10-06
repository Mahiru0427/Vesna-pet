from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import importlib.util,subprocess,json,wave,math
import imageio_ffmpeg

BASE=Path(__file__).resolve().parent.parent
WORK=BASE/'build'; WORK.mkdir(exist_ok=True)
OUT=BASE/'build'; OUT.mkdir(exist_ok=True)
class Render:
    ROW_DURATIONS = {'idle': [280, 110, 110, 140, 140, 320], 'running-right': [120, 120, 120, 120, 120, 120, 120, 220], 'running-left': [120, 120, 120, 120, 120, 120, 120, 220], 'waving': [140, 140, 140, 280], 'jumping': [140, 140, 140, 140, 280], 'failed': [140, 140, 140, 140, 140, 140, 140, 240], 'waiting': [150, 150, 150, 150, 150, 260], 'running': [120, 120, 120, 120, 120, 220], 'review': [150, 150, 150, 150, 150, 280]}
    @staticmethod
    def save_preview(frames,durations,path):
        frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2)
render=Render()
FPS=30; SIZE=(1080,1920); BG='#EAF8F6'; INK='#184F58'; SOFT='#527D80'
cartoon={n:ImageFont.truetype(str(BASE/'fonts/ZCOOLKuaiLe-Regular.ttf'),n) for n in [52,62,80,106]}
names=['待机 · 眨眨眼','向右跑','向左跑','挥手 · 和你打招呼','跳跃 · 轻轻一蹦','失落 · 有点小沮丧','等待 · 轮到你啦','思考 · 认真工作中','检查 · 再确认一下']
row_names=list(render.ROW_DURATIONS)+['look-row-9','look-row-10']
def cell(row,col): return Image.open(BASE/'source/render-frames'/row_names[row]/f'{col:02}.png').convert('RGBA')
def centered(draw,text,y,font,color=INK,stroke=0):
    box=draw.textbbox((0,0),text,font=font); draw.text(((1080-(box[2]-box[0]))/2,y-box[1]),text,font=font,fill=color,stroke_width=stroke,stroke_fill='white')
def scene(sprite,label,ending=False):
    im=Image.new('RGB',SIZE,BG); d=ImageDraw.Draw(im)
    centered(d,'桌宠动作展示',100,cartoon[62])
    if ending:
        sprite=sprite.resize((765,1232),Image.Resampling.LANCZOS); im.paste(sprite,(157,80),sprite)
        centered(d,'麻烦三连',1320,cartoon[106],'#247A80',8)
        centered(d,'给我回回血喵',1470,cartoon[106],'#247A80',8)
        centered(d,'谢谢喵',1640,cartoon[80],'#D98397',7)
    else:
        centered(d,'小风仙上线啦',210,cartoon[62],SOFT)
        im.paste(sprite,(90,150),sprite)
        centered(d,label,1650,cartoon[62])
    return im

segments=[]
segments.append({'title':'开场','frames':[scene(cell(0,0),'来认识一下小风仙吧')],'counts':[54]})
for row,((state,durations),name) in enumerate(zip(render.ROW_DURATIONS.items(),names)):
    frames=[scene(cell(row,col),name) for col in range(len(durations))]
    counts=[max(1,round(ms*FPS/1000)) for ms in durations]
    segments.append({'title':name,'frames':frames*2,'counts':counts*2,'source_row':row})
lookframes=[scene(cell(9+i//8,i%8),'转头注视 · 看看四周') for i in range(16)]
segments.append({'title':'转头注视','frames':lookframes,'counts':[8]*16,'source_rows':[9,10]})
ending_start=sum(sum(s['counts']) for s in segments)/FPS
end_frames=180
wave_durations=render.ROW_DURATIONS['waving']; wave_counts=[round(t*FPS/1000) for t in wave_durations]
ending=[]; ec=[]; remaining=end_frames
while remaining:
    for col,c in enumerate(wave_counts):
        n=min(c,remaining); ending.append(scene(cell(3,col),'',True)); ec.append(n); remaining-=n
        if remaining==0: break
segments.append({'title':'三连收尾','frames':ending,'counts':ec})
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
final=OUT/'vesna-showcase.mp4'
proc=subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-threads','4','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(final)],stdin=subprocess.PIPE)
for seg in segments:
    for im,count in zip(seg['frames'],seg['counts']):
        buf=im.tobytes()
        for _ in range(count): proc.stdin.write(buf)
proc.stdin.close()
if proc.wait()!=0: raise RuntimeError('video encoding failed')
previewframes=[]; previewds=[]
for seg in segments:
    for im,count in zip(seg['frames'],seg['counts']):
        previewframes.append(im.resize((270,480),Image.Resampling.LANCZOS)); previewds.append(round(count/FPS*1000))
render.save_preview(previewframes,previewds,OUT/'小风仙桌宠展示_白丝修正预览.gif')
segments[0]['frames'][0].save(OUT/'小风仙桌宠展示_白丝修正封面.png')
segments[-1]['frames'][0].save(OUT/'小风仙桌宠展示_白丝修正结尾.png')
qa=Image.new('RGB',(1080,1280),BG)
selected=[segments[i]['frames'][0] for i in [0,1,4,5,10,11]]
for i,im in enumerate(selected): qa.paste(im.resize((360,640)),((i%3)*360,(i//3)*640))
qa.save(WORK/'video-contact-stockings.png')
timeline=[]; position=0
for s in segments:
    duration=sum(s['counts'])/FPS
    timeline.append({'title':s['title'],'start':round(position,3),'duration':round(duration,3)})
    position+=duration
report={'file':str(final),'size':[1080,1920],'fps':FPS,'total_frames':sum(sum(s['counts']) for s in segments),'duration':round(position,3),'audio_streams':0,'source_required_frames':73,'timeline':timeline,'ending_text':'麻烦三连给我回回血喵 谢谢喵','subtitle':'小风仙上线啦','font':'ZCOOL KuaiLe (OFL)','background':BG,'pet_pixels':'original high-resolution generated action strips; shared-scale extraction and background cleanup before rendering, no 192x208 atlas upscaling'}
(WORK/'video-report-stockings.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
