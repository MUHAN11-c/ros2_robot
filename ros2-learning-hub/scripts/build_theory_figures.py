#!/usr/bin/env python3
"""生成原创理论图解与连续教材的交互静态替代图。

坐标图使用米和弧度定义数学关系，SVG 位置单位仅为显示像素。
预测、规划图明确为教学示意，不把绘图路径冒充算法实测结果。
"""
import json
import math
import hashlib
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'dist/preview/figures'


def text(x,y,value,size=16,color='#526c5a',weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(str(value))}</text>'


def line(x1,y1,x2,y2,color='#769481',dash='',arrow=True,width=2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"' if dash else '')+(' marker-end="url(#arrow)"' if arrow else '')+'/>'


def box(x,y,w,h,title,subtitle,fill='#edf5ed'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="#c8dbc8"/>'+text(x+16,y+29,title,17,'#345b3b',600)+text(x+16,y+53,subtitle,12)


def svg(title,description,body):
    subtitle={'同一个点，两种坐标表达':'先转换分量，再改变原点','二维交互的静态数值案例':'一个可以手算的90°案例','用预测和测量修正状态':'状态和不确定性一起递推','比较搜索时，先对齐同一个问题':'障碍图、代价函数和启发式','预测多步，执行一步，重新观测':'模型预测与滚动执行','SLAM：状态由哪些约束连接？':'运动、观测和回环形成约束','连杆、局部关节轴与末端位置':'默认姿态与末端数值','组件参数：来源、覆盖与实际值':'先分清来源，再核对覆盖顺序'}[title]
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 470" role="img" aria-labelledby="title desc"><title id="title">'+escape(title)+'</title><desc id="desc">'+escape(description)+'</desc><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill="#769481"/></marker></defs><rect width="900" height="470" fill="#fbfdf9"/><g font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif">'+text(30,42,subtitle,23,'#294b32',650)+body+'</g></svg>\n'


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    figures=[]
    def save(identifier,title,description,body,caption,placements,book_only=False):
        filename=identifier+'.svg'
        (DEST/filename).write_text(svg(title,description,body))
        item=dict(id=identifier,file='preview/figures/'+filename,title=title,kind='原理图',alt=description,caption=caption,
                  placements=[dict(chapter=c,afterSection=i) for c,i in placements])
        if book_only:item['bookOnly']=True
        figures.append(item)

    body=line(125,340,490,340)+line(125,340,125,65)
    body+=line(285,260,285,65,'#b67a4b')+line(285,260,140,260,'#b67a4b')
    body+=line(285,100,285,340,'#a8bca3','5 5',False,1)+line(285,100,125,100,'#a8bca3','5 5',False,1)
    body+='<circle cx="285" cy="100" r="7" fill="#4f83a0"/>'
    for values in [(100,365,'B'),(490,362,'x_B'),(90,65,'y_B'),(294,255,'L'),(298,80,'x_L'),(145,247,'y_L'),(302,105,'同一个物理点')]:body+=text(*values)
    body+=box(540,94,320,75,'先旋转，再平移','p_B = R(θ) · p_L + t')
    for y,value in [(207,'θ = 90° = π/2 rad'),(242,'t = [1, 0.5] m'),(277,'p_L = [1, 0] m'),(312,'p_B = [1, 1.5] m'),(371,'逆变换先减 t，再乘 Rᵀ')]:body+=text(560,y,value)
    body+=text(45,425,'旋转矩阵无量纲；平移和点坐标使用同一长度单位。',14)
    save('rigid-composition','同一个点，两种坐标表达','车体B与旋转90度的传感器L坐标系，以及点坐标的旋转平移数值案例。',body,'例中先将传感器坐标旋转90°，再加安装平移。图上两组坐标描述同一个点；改变表达坐标不改变物理点。', [('math-rigid',0),('math-kinematics',0)])
    save('tf2-static','二维交互的静态数值案例','二维刚体变换的默认可手算案例，米为长度单位。',body,'连续版保存一个静态参数案例；交互版可在相关章节调整平移与旋转。', [('tf2',2),('eco-tf-frames',1)],True)

    body=box(40,102,235,78,'预测','状态 x⁻，协方差 P⁻')+box(335,102,235,78,'创新与一致性','r = z − h(x⁻)')+box(630,102,230,78,'校正','状态 x⁺，协方差 P⁺')
    body+=line(275,140,335,140)+line(570,140,630,140)
    body+=box(40,264,235,75,'运动与过程噪声','模型、控制输入、Q')+box(335,264,235,75,'测量与噪声','传感器观测 z、R')+box(630,264,230,75,'下一轮','保存时间与坐标合同')
    body+=line(155,264,155,180)+line(450,264,450,180)+line(745,180,745,264)
    body+='<path d="M745 339V384H155V180" fill="none" stroke="#769481" stroke-width="2" marker-end="url(#arrow)"/>'
    body+=text(40,433,'图示为滤波估计流程；线性、高斯、独立性与可观性条件须按正文核对。',14)
    save('estimation-loop','用预测和测量修正状态','运动预测、创新、测量校正和协方差递推的闭环。',body,'预测与校正既要更新状态，也要处理不确定性、时间戳和观测坐标。图不意味着所有SLAM算法都采用EKF，也不保证所有状态都可观。', [('math-estimation',1),('eco-state-estimation',0)])

    obstacles={(4,y) for y in range(3,6)}|{(6,0),(6,1),(2,1),(3,1)}
    path=[(0,5),(1,5),(1,4),(2,4),(2,3),(3,3),(3,2),(4,2),(5,2),(6,2),(7,2),(8,2),(8,1),(9,1),(9,0)]
    body=''
    for y in range(6):
        for x in range(10):body+=f'<rect x="{45+x*45}" y="{95+y*45}" width="43" height="43" rx="2" fill="'+('#78927b' if (x,y) in obstacles else '#edf3e8')+'"/>'
    points=' '.join(f'{67+x*45},{117+y*45}' for x,y in path)
    body+=f'<polyline points="{points}" fill="none" stroke="#c18143" stroke-width="5" stroke-linejoin="round"/>'
    body+=line(67,342,472,117,'#87a87d','6 5',False)
    body+=text(58,349,'S',18,'#294b32',700)+text(463,124,'G',18,'#294b32',700)
    for y,value in [(120,'Dijkstra：优先累计代价 g'),(166,'A*：优先 f = g + h'),(212,'h 是估计，不是额外实测成本'),(258,'邻接方式、分辨率、代价需对齐'),(304,'未知区域和障碍膨胀改变问题')]:body+=text(535,y,value,15)
    body+=text(45,425,'网格路径仅作示意；搜索最优性和机器人可执行性是两个层次。',14)
    save('planning-search','比较搜索时，先对齐同一个问题','网格、障碍、起终点和示意路径，以及Dijkstra和A星的优先级。',body,'虚线是理想距离直觉，橙线是绕障示意路径，未把这条绘制路径标为算法最优输出。真实最优性要以相同图、非负代价和启发条件核查；机器人还需要运动学与碰撞约束。', [('theory-planning',1),('project-navigation',2)])

    body=line(65,335,520,335)+line(65,335,65,85)
    trajectory=[(65,112),(120,165),(175,209),(230,244),(285,273),(340,294),(395,309),(450,319),(505,325)]
    body+='<polyline points="'+' '.join(f'{x},{y}' for x,y in trajectory)+'" fill="none" stroke="#5b8d62" stroke-width="3" stroke-dasharray="7 5"/>'
    body+='<circle cx="65" cy="112" r="7" fill="#b98048"/>'
    body+=text(33,80,'状态')+text(453,363,'预测步 k')
    for k,(x,y) in enumerate(trajectory):body+=text(x-3,357,k,11)
    body+=box(565,93,295,74,'优化一个预测时域','模型、代价、约束、当前状态')+box(565,210,295,74,'只执行第一个控制量','控制周期 Δt，单位 s')+box(565,327,295,74,'获得新测量，再优化','可行性、求解耗时和降级策略')
    body+=line(712,167,712,210)+line(712,284,712,327)
    body+=text(45,429,'轨迹为教学示意；滚动优化不自动构成稳定性或硬实时保证。',14)
    save('receding-horizon','预测多步，执行一步，重新观测','模型预测控制的预测时域与滚动执行顺序。',body,'示意轨迹没有替代具体模型或求解器结果。实际系统需检查约束可行性、终端条件、采样周期、求解上界和失败后的控制策略。', [('theory-optimal-control',2),('math-control',4)])

    body=box(65,195,170,72,'位姿 x₀','固定一个参考自由度')+box(360,195,170,72,'位姿 x₁','相邻运动约束')+box(655,195,170,72,'位姿 x₂','相邻运动约束')
    body+=line(235,230,360,230)+line(530,230,655,230)
    body+=box(360,83,170,65,'地标 ℓ','观测约束', '#fff2df')
    body+=line(150,195,390,148,'#b28a55')+line(445,195,445,148,'#b28a55')+line(740,195,500,148,'#b28a55')
    body+='<path d="M740 277C740 390 150 390 150 277" fill="none" stroke="#789b6c" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#arrow)"/>'
    body+=text(333,380,'回环：加入历史约束',16)+text(65,430,'残差、噪声模型、数据关联与规范自由度共同决定优化问题。',14)
    save('slam-constraints','SLAM：状态由哪些约束连接？','三个机器人位姿、一个地标、运动与观测约束以及回环边。',body,'方框是待估计变量，连接表示模型残差或测量约束。回环需要可靠的数据关联；固定一个参考自由度可消除相应规范歧义，但不能自动修复错误观测或保证地图准确。', [('theory-slam',1)])

    # 静态三维模型使用与浏览器交互相同的几何参数：连杆0.85/0.65m，肩高0.4m。
    q1,q2,q3=map(math.radians,(25,-40,70))
    shoulder=(0,0,.4)
    elbow=(.85*math.cos(q2)*math.cos(q1),.85*math.cos(q2)*math.sin(q1),.4-.85*math.sin(q2))
    wrist=(elbow[0]+.65*math.cos(q2+q3)*math.cos(q1),elbow[1]+.65*math.cos(q2+q3)*math.sin(q1),elbow[2]-.65*math.sin(q2+q3))
    def project(p):
        x,y,z=p; a,e=map(math.radians,(-30,24)); x-=.4; z-=.4
        horizontal=math.cos(a)*x-math.sin(a)*y; along=math.sin(a)*x+math.cos(a)*y
        return round(290+220*horizontal,2),round(292-220*(math.cos(e)*z-math.sin(e)*along),2)
    body=''
    for i in range(-3,6):
        for start,end in [((i*.25,-.75,0),(i*.25,1.25,0)),((-.75,i*.25,0),(1.25,i*.25,0))]:
            a,b=project(start),project(end);body+=line(*a,*b,'#dde9d8','',False,1)
    nodes=[(0,0,0),shoulder,elbow,wrist]
    for start,end in zip(nodes,nodes[1:]):body+=line(*project(start),*project(end),'#53805a','',False,16)
    for point in nodes:
        x,y=project(point);body+=f'<circle cx="{x}" cy="{y}" r="9" fill="#355d3d" stroke="#edf4e8" stroke-width="3"/>'
    body+=box(560,100,300,75,'局部关节轴决定运动','q₁绕Z，q₂/q₃绕局部Y')
    for y,value in [(224,'q = [25°, −40°, 70°]'),(266,'连杆长度：0.85 m / 0.65 m'),(309,'末端坐标（m）：'),(343,'['+', '.join(f'{v:.3f}' for v in wrist)+']')]:body+=text(578,y,value,15)
    body+=text(45,430,'正交投影；视角改变只改变显示，关节角改变才改变几何姿态。',14)
    save('robot-static','连杆、局部关节轴与末端位置','三关节机器人几何模型，显示与交互模型一致的默认关节角和末端坐标。',body,'这是交互模型默认姿态的静态几何图，仅验证运动学关系，不包含质量、碰撞、接触、驱动或ROS连接。交互版可在正文中调整视角和关节。', [('eco-model-rviz',1),('eco-moveit-planning',1),('math-kinematics',2),('project-manipulation',2)],True)

    # 第3轮同一Config类的已测输入：gain无量纲，Float64数值合同为m/s。
    # 管理节点当前参数与Context全局CLI是不同存储；图中不画不存在的自动同步箭头。
    component_evidence=ROOT/'validation-evidence/component-labs-current-validation.json'
    component_report=json.loads(component_evidence.read_text())
    if component_report.get('passed') is not True:
        raise ValueError('参数来源图需要通过的第3轮组件实测')
    measured=next(item['result']['measurements'] for item in component_report['results'] if item['case']=='component_parameters')
    configs={item['label']:item for item in measured['configurations']}
    expected={'default_config':(1.0,0.2),'forward_config':(1.8,0.36),
              'local_config':(1.5,0.3),'forward_local':(1.5,0.3),'forward_after_manager_change':(1.8,0.36)}
    if measured['managerStartupGain']!=1.8 or measured['managerGainAfterChange']!=1.2:
        raise ValueError('管理参数实测输入已变化，需要先核对图中文字')
    for name,(gain,output) in expected.items():
        if configs[name]['gain']!=gain or not math.isclose(configs[name]['outputMps'],output,rel_tol=0,abs_tol=1e-12):
            raise ValueError('参数来源图的数值与报告不一致：'+name)
    body=box(30,85,260,88,'进程Context全局CLI','启动时 gain = 1.8')
    body+=box(330,85,240,88,'管理节点自身参数','启动1.8，之后set为1.2','#fff2df')
    body+=text(346,160,'管理当前值单独查询',12)
    body+=box(610,85,260,88,'本次LoadNode.parameters','局部 gain = 1.5')
    body+=line(160,173,160,235)+text(32,213,'forward=true时进入',12)
    body+=line(740,173,740,212,arrow=False)+line(740,212,310,212,arrow=False)+line(310,212,310,235)
    body+=text(620,198,'装载请求的局部覆盖',12)
    body+=box(80,235,310,75,'装载组件的NodeOptions','manager默认不转发全局参数')
    body+=box(510,235,310,75,'显式声明并校验gain','默认1.0；有限DOUBLE范围[0,2]')
    body+=line(390,273,510,273)+text(401,257,'局部覆盖优先',12)
    body+=text(30,335,'同一Config类，三种装载输入的实测结果',14,'#345b3b',600)
    body+=box(30,347,260,75,'不转发＋无局部值','gain=1.0 → 0.20 m/s')
    body+=box(320,347,260,75,'转发＋无局部值','gain=1.8 → 0.36 m/s')
    body+=box(610,347,260,75,'提供局部gain=1.5','gain=1.5 → 0.30 m/s')
    body+=text(30,453,'输出为0.2 m/s × gain；三个结果来自不同加载实例，管理参数修改不改写Context CLI。',13)
    save('component-options','组件参数：来源、覆盖与实际值',
         'Context全局CLI、管理节点当前参数和LoadNode局部覆盖分开；转发开关控制全局CLI，局部覆盖优先，三个实例输出0.20、0.36、0.30米每秒。',body,
         '本图针对标准manager创建的组件options，数值取自第3轮真实Config实验。管理节点从1.8改为1.2不改写Context的启动CLI；局部加载参数优先。gain无量纲，输出按0.2m/s基值换算；不是硬件速度或任意NodeOptions默认值的示意。',
         [('composition',6)])
    figures[-1].update(evidenceFile=component_evidence.relative_to(ROOT).as_posix(),
                       evidenceSha256=hashlib.sha256(component_evidence.read_bytes()).hexdigest())

    path=ROOT/'source/design-figures.json'
    data=json.loads(path.read_text())
    identifiers={item['id'] for item in figures}
    data['figures']=[item for item in data['figures'] if item['id'] not in identifiers]+figures
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'newFigures':len(figures),'totalStaticFigures':len(data['figures'])}))


if __name__=='__main__':main()
