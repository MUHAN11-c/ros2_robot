#!/usr/bin/env python3
"""应用教材的八个离线数值实验，只使用 Python 标准库。

输入：可选的 --case 名称；省略时运行全部实验。所有输入数据写在函数中，
修改前先查看单位与假设。输出：可解释的数值结果及断言；断言失败即退出非零。
这些实验不连接 ROS、仿真器或硬件，不向机器人发布任何控制命令。
"""

from __future__ import annotations

import argparse


def engineering_lab():
    """检查延迟预算与测量新鲜度；这是模型验算，不是实际实时性测试。"""
    from math import ceil, isclose

    # 输入：所有时间以秒表示；周期 0.02 s 对应名义 50 Hz。
    deadline_s = 0.020
    stages_s = {"感知": 0.004, "排队": 0.007, "求解": 0.003, "发布": 0.002}
    total_s = sum(stages_s.values())
    assert isclose(total_s, 0.016)
    assert total_s < deadline_s
    # 边界：排队额外增加 0.009 s 后越过截止期，不能靠平均频率掩盖。
    assert total_s + 0.009 > deadline_s

    # 输入：同一时钟下的当前时刻、采样时刻与允许测量年龄，单位均为秒。
    now_s, max_age_s = 0.120, 0.030
    timestamps_s = [0.000, 0.020, 0.040, 0.100, 0.130]
    accepted = [t for t in timestamps_s if 0.0 <= now_s - t <= max_age_s]
    assert accepted == [0.100]  # 过旧数据和未来时间戳都拒绝。
    # 容量下界只针对“生产者暂停消费 0.06 s”的确定性模型，不保证调度实时性。
    capacity = ceil(50.0 * 0.060) + 1
    assert capacity == 4
    result = {"预算总延迟_ms": total_s * 1000, "余量_ms": (deadline_s-total_s)*1000,
              "接收时间戳_s": accepted, "建议最小缓存槽": capacity}
    print("工程预算", result)
    return result


def slam_lab():
    """求解固定第一帧的一维位姿图，并检验未固定时的平移规范自由度。"""
    from math import isclose

    # 输入：相邻位移 z01=z12=1.1 m，回环位移 z02=2.0 m；相同方差可约掉。
    # 固定 x0=0 后，最小化 (x1-1.1)^2+(x2-x1-1.1)^2+(x2-2.0)^2。
    h00, h01, h11 = 2.0, -1.0, 2.0
    b0, b1 = 0.0, 3.1
    determinant = h00*h11 - h01*h01
    assert determinant > 0.0  # 这个带锚点的小问题有唯一解。
    x1 = (h11*b0 - h01*b1) / determinant
    x2 = (-h01*b0 + h00*b1) / determinant

    def cost(a, b):
        return (a-1.1)**2 + (b-a-1.1)**2 + (b-2.0)**2

    assert isclose(x1, 1.0333333333333334)
    assert isclose(x2, 2.066666666666667)
    assert cost(x1, x2) < cost(1.1, 2.2)
    # 未锚定的三节点拉普拉斯矩阵乘全一向量为零：整体平移不改变相对残差。
    h_free = ((2,-1,-1), (-1,2,-1), (-1,-1,2))
    assert all(sum(row) == 0 for row in h_free)
    residuals = (x1-1.1, x2-x1-1.1, x2-2.0)
    # 在该一维线性模型中，梯度 J^T r 应为零；不等于每条测量都完全满足。
    assert abs(residuals[0]-residuals[1]) < 1e-12
    assert abs(residuals[1]+residuals[2]) < 1e-12
    result = {"x1_m": x1, "x2_m": x2, "优化前代价_m2": cost(1.1,2.2),
              "优化后代价_m2": cost(x1,x2)}
    print("一维位姿图", result)
    return result


def planning_lab():
    """在四邻接、单位正代价、点机器人模型中比较 A* 与 Dijkstra。"""
    import heapq

    width, height, resolution_m = 7, 5, 0.1
    start, goal = (0,0), (6,0)
    walls = {(3,y) for y in range(4)}  # 顶部 y=4 留一个通道。

    def search(obstacles, use_heuristic):
        # g 的单位是格数；启发式是到目标的曼哈顿格数，与四邻接模型一致。
        def heuristic(p):
            return abs(p[0]-goal[0])+abs(p[1]-goal[1]) if use_heuristic else 0
        if start in obstacles or goal in obstacles:
            return None
        heap = [(heuristic(start),0,start)]
        distance, previous = {start:0}, {}
        while heap:
            _, g, current = heapq.heappop(heap)
            if g != distance.get(current):
                continue  # 跳过已被更短路径取代的旧队列项。
            if current == goal:
                path = [goal]
                while path[-1] != start:
                    path.append(previous[path[-1]])
                return list(reversed(path))
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt = current[0]+dx, current[1]+dy
                if not (0 <= nxt[0] < width and 0 <= nxt[1] < height):
                    continue
                if nxt in obstacles:
                    continue
                new_g = g+1
                if new_g < distance.get(nxt,float("inf")):
                    distance[nxt], previous[nxt] = new_g,current
                    heapq.heappush(heap,(new_g+heuristic(nxt),new_g,nxt))
        return None  # 队列耗尽是明确的无路结果，不能继续执行旧路径。

    path_a = search(walls,True)
    path_d = search(walls,False)
    assert path_a is not None and path_d is not None
    assert len(path_a)-1 == len(path_d)-1 == 14
    assert all(p not in walls for p in path_a)
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(path_a,path_a[1:]))
    assert search(walls | {(3,4)},True) is None
    result = {"最优步数": len(path_a)-1, "路径长度_m": (len(path_a)-1)*resolution_m,
              "封闭通道结果": "无路"}
    print("网格搜索", result)
    return result


def optimal_control_lab():
    """有限时域标量 LQR；验证 Riccati 值函数与直接累计代价一致。"""
    from math import isclose

    # 输入：x 为位置/1 m，u 为速度/(1 m/s)，均无量纲；b=采样周期 0.1 s。
    a, b, q, r, terminal, horizon = 1.0, 0.1, 1.0, 0.1, 5.0, 20
    assert r > 0 and q >= 0 and terminal >= 0
    p = [0.0]*(horizon+1)
    gains = [0.0]*horizon
    p[horizon] = terminal
    # 顺序一：从终点向起点回推，与随后正向运行的顺序相反。
    for k in range(horizon-1,-1,-1):
        denominator = r+b*b*p[k+1]
        gains[k] = a*b*p[k+1]/denominator
        p[k] = q+a*a*p[k+1]-(a*b*p[k+1])**2/denominator
        assert p[k] >= 0
    # 顺序二：只在无约束模型里使用精确最优反馈，不把裁剪输入称为约束最优解。
    x, x0, total = 2.0, 2.0, 0.0
    first_u = None
    for k,gain in enumerate(gains):
        u = -gain*x
        first_u = u if k == 0 else first_u
        total += q*x*x+r*u*u
        x = a*x+b*u
    total += terminal*x*x
    assert isclose(total,p[0]*x0*x0,rel_tol=1e-12)
    zero_input_cost = (horizon*q+terminal)*x0*x0
    assert total < zero_input_cost and abs(x) < abs(x0)
    result = {"初始最优速度_m_s": first_u, "末端位置_m": x,
              "最优代价": total, "零输入代价": zero_input_cost}
    print("有限时域 LQR", result)
    return result


def legged_lab():
    """LIPM 精确解：展示 ZMP 在支撑区内仍不足以保证无需迈步地停止。"""
    import math

    # 输入：平地、恒质心高度、无角动量变化、无外扰的一维简化模型。
    # c、z、h 单位 m；v 单位 m/s；g 单位 m/s²；omega 单位 s^-1。
    h, g, c0, v0, z, half_support = 0.8, 9.81, 0.03, 0.35, 0.0, 0.10
    omega = math.sqrt(g/h)
    capture = c0+v0/omega

    def exact(t_s, initial_v, zmp):
        c = zmp+(c0-zmp)*math.cosh(omega*t_s)+initial_v/omega*math.sinh(omega*t_s)
        v = omega*(c0-zmp)*math.sinh(omega*t_s)+initial_v*math.cosh(omega*t_s)
        return c,v

    c_half,v_half = exact(0.5,v0,z)
    assert -half_support <= z <= half_support
    assert capture > half_support and c_half > half_support
    # 对较小的初速度，选择可达捕获点作为恒定 ZMP，可消除发散分量。
    slow_v = 0.10
    feasible_capture = c0+slow_v/omega
    assert abs(feasible_capture) < half_support
    c_slow,v_slow = exact(1.0,slow_v,feasible_capture)
    assert abs(v_slow) < slow_v
    assert math.isclose(c_slow+v_slow/omega,feasible_capture,abs_tol=1e-12)
    result = {"快运动捕获点_m": capture, "固定ZMP半秒后质心_m": c_half,
              "慢运动捕获点_m": feasible_capture, "慢运动一秒后速度_m_s": v_slow}
    print("足式简化模型", result)
    return result


def aerial_lab():
    """检查 ENU/NED、FLU/FRD 的向量变换与理想四旋翼悬停推力。"""
    import math

    def enu_to_ned(v):
        # 输入/输出都是同一种物理量；位置用 m，速度用 m/s，不能混用。
        east,north,up = v
        return north,east,-up

    def flu_to_frd(v):
        forward,left,up = v
        return forward,-left,-up

    vector_enu_m = (1.0,2.0,3.0)
    vector_ned_m = enu_to_ned(vector_enu_m)
    assert vector_ned_m == (2.0,1.0,-3.0)
    assert enu_to_ned(vector_ned_m) == vector_enu_m
    assert flu_to_frd(flu_to_frd(vector_enu_m)) == vector_enu_m
    assert math.isclose(sum(v*v for v in vector_enu_m),sum(v*v for v in vector_ned_m))
    # 理想水平悬停：总推力为 mg；此处 N 不能直接写入归一化推力消息。
    mass_kg,g_m_s2 = 1.5,9.81
    total_thrust_n = mass_kg*g_m_s2
    thrust_per_rotor_n = total_thrust_n/4
    assert math.isclose(4*thrust_per_rotor_n/mass_kg-g_m_s2,0.0,abs_tol=1e-12)
    result = {"ENU位置_m": vector_enu_m, "NED位置_m": vector_ned_m,
              "总悬停推力_N": total_thrust_n, "每旋翼推力_N": thrust_per_rotor_n}
    print("无人机坐标与推力", result)
    return result


def navigation_lab():
    """计算延迟加恒减速停车距离，并检查导航任务结果的幂等处理。"""
    import math

    # 输入：车速 m/s，感知到制动的延迟 s，有效减速度正值 m/s²。
    speed_m_s,latency_s,deceleration_m_s2 = 0.6,0.2,0.8
    assert speed_m_s >= 0 and latency_s >= 0 and deceleration_m_s2 > 0
    reaction_m = speed_m_s*latency_s
    brake_m = speed_m_s**2/(2*deceleration_m_s2)
    stop_m = reaction_m+brake_m
    assert math.isclose(stop_m,0.345)
    assert stop_m < 2*speed_m_s*latency_s+(2*speed_m_s)**2/(2*deceleration_m_s2)
    # 输入事件可能重复；只接受当前任务的首个终态，旧任务回调不能覆盖新任务。
    active_goal, terminal = "goal-B", None
    events = [("goal-A","SUCCEEDED"),("goal-B","CANCELED"),("goal-B","SUCCEEDED")]
    for goal_id,status in events:
        if goal_id == active_goal and terminal is None:
            terminal = status
    assert terminal == "CANCELED"
    result = {"反应距离_m": reaction_m, "制动距离_m": brake_m,
              "理想停车总距离_m": stop_m, "当前任务唯一终态": terminal}
    print("导航任务合同", result)
    return result


def manipulation_lab():
    """验证单关节静止到静止五次轨迹的端点与全程速度、加速度上界。"""
    import math

    # 输入：关节角差 rad，速度限制 rad/s，加速度限制 rad/s²。
    q0,q1,v_limit,a_limit = 0.0,1.2,0.6,1.0
    delta = q1-q0
    # s(tau)=10tau³-15tau⁴+6tau⁵；其导数极值可解析求得。
    # 常数 1.875 与 10/sqrt(3) 是该特定五次曲线的极值，不适用于任意轨迹。
    duration_s = max(1.875*abs(delta)/v_limit,
                     math.sqrt((10/math.sqrt(3))*abs(delta)/a_limit))

    def sample(t_s):
        tau = t_s/duration_s
        assert 0.0 <= tau <= 1.0
        s = 10*tau**3-15*tau**4+6*tau**5
        sd = 30*tau**2-60*tau**3+30*tau**4
        sdd = 60*tau-180*tau**2+120*tau**3
        return q0+delta*s,delta*sd/duration_s,delta*sdd/duration_s**2

    assert sample(0.0) == (q0,0.0,0.0)
    end = sample(duration_s)
    assert math.isclose(end[0],q1) and abs(end[1])+abs(end[2]) < 1e-12
    values = [sample(duration_s*i/1000) for i in range(1001)]
    assert max(abs(v[1]) for v in values) <= v_limit+1e-12
    assert max(abs(v[2]) for v in values) <= a_limit+1e-12
    # 端点速度/加速度为零并不表示 jerk 也为零，更不证明多关节路径无碰撞。
    result = {"轨迹时间_s": duration_s, "最大采样速度_rad_s": max(abs(v[1]) for v in values),
              "最大采样加速度_rad_s2": max(abs(v[2]) for v in values)}
    print("机械臂时间参数化", result)
    return result


CASES = {"engineering":engineering_lab, "slam":slam_lab, "planning":planning_lab,
         "optimal-control":optimal_control_lab, "legged":legged_lab, "aerial":aerial_lab,
         "navigation":navigation_lab, "manipulation":manipulation_lab}


def main():
    """只选择并运行离线实验；未知名称由 argparse 拒绝。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case",choices=CASES,help="省略时执行全部八个实验")
    args = parser.parse_args()
    selected = [args.case] if args.case else list(CASES)
    for name in selected:
        CASES[name]()
    print(f"通过：{len(selected)} 个离线应用实验；ROS、仿真与硬件均未连接。")


if __name__ == "__main__":
    main()
