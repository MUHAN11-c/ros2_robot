#!/usr/bin/env python3
"""八章机器人数学的标准库实验。

输入：--chapter 选择章节ID；缺省执行全部。所有教学输入在各函数内部固定。
输出：每章带单位的结果与断言；不访问ROS图，不发送机器人控制命令。
执行顺序：解析参数 → 调用指定章节函数 → 输出汇总。
边界：只验证注释中声明的小型理想模型，不替代数值库、仿真或硬件验证。
"""

def lab_linear():
    import math

    def solve2(matrix, vector):
        # 教学用二阶线性方程求解器；输入的两行长度均为 2。
        # 1e-12 是本例量纲统一后的绝对退化阈值，不是通用数值策略。
        a, b = matrix[0]
        c, d = matrix[1]
        determinant = a * d - b * c
        if abs(determinant) < 1e-12:
            raise ValueError('观测退化：不能唯一求解两个未知量')
        return [(d * vector[0] - b * vector[1]) / determinant,
                (-c * vector[0] + a * vector[1]) / determinant]

    # 状态为 [x, y]，单位 m；每行观测系数无量纲，b 的单位为 m。
    matrix = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    observations = [1.0, 2.0, 2.8]
    # W=I：三个观测具有相同方差。先形成 H=A^T A 和 g=A^T b。
    hessian = [[sum(row[i] * row[j] for row in matrix)
                for j in range(2)] for i in range(2)]
    gradient_rhs = [sum(row[i] * z for row, z in zip(matrix, observations))
                    for i in range(2)]
    estimate = solve2(hessian, gradient_rhs)
    residual = [sum(a * x for a, x in zip(row, estimate)) - z
                for row, z in zip(matrix, observations)]
    # 验收一：最小二乘残差应正交于 A 的两列，误差容差单位为 m。
    normal_residual = [sum(row[i] * r for row, r in zip(matrix, residual))
                       for i in range(2)]
    assert max(map(abs, normal_residual)) < 1e-12
    assert math.isclose(estimate[0], 14.0 / 15.0, abs_tol=1e-12)
    assert math.isclose(estimate[1], 29.0 / 15.0, abs_tol=1e-12)

    # 验收二：带权情形也必须满足 A^T W r=0；权重的共同缩放不改变解。
    weights = [1.0, 4.0, 1.0]
    weighted_h = [[sum(w * row[i] * row[j] for row, w in zip(matrix, weights))
                   for j in range(2)] for i in range(2)]
    weighted_g = [sum(w * row[i] * z for row, z, w in zip(matrix, observations, weights))
                  for i in range(2)]
    weighted_x = solve2(weighted_h, weighted_g)
    weighted_r = [sum(a * x for a, x in zip(row, weighted_x)) - z
                  for row, z in zip(matrix, observations)]
    assert all(abs(sum(w * row[i] * r for row, r, w in zip(matrix, weighted_r, weights))) < 1e-12
               for i in range(2))

    # 验收三：重复方向观测不会增加秩，显式拒绝奇异方程。
    try:
        solve2([[1.0, 1.0], [2.0, 2.0]], [1.0, 2.0])
    except ValueError:
        pass
    else:
        raise AssertionError('奇异矩阵本应被拒绝')

    # 协方差单位 m^2；投影 s=x+y 时必须包括相关项 2*cov(x,y)。
    covariance = [[0.04, 0.03], [0.03, 0.09]]
    variance_sum = sum(sum(row) for row in covariance)
    assert covariance[0][0] > 0.0
    assert covariance[0][0] * covariance[1][1] - covariance[0][1] ** 2 > 0.0
    assert math.isclose(variance_sum, 0.19, abs_tol=1e-12)
    # 本例 H 的特征值是 1、3，所以谱条件数为 3；A 的条件数为 sqrt(3)。
    trace = hessian[0][0] + hessian[1][1]
    gap = math.sqrt((hessian[0][0] - hessian[1][1]) ** 2 + 4 * hessian[0][1] ** 2)
    condition_h = (trace + gap) / (trace - gap)
    assert math.isclose(condition_h, 3.0, abs_tol=1e-12)
    result = {'x_m': estimate, 'residual_m': residual, 'variance_sum_m2': variance_sum,
              'condition_normal_matrix': condition_h}
    print('线性代数实验通过：', result)
    return result

def lab_rigid():
    import math

    def rotate2(angle_rad, point_m):
        # 列向量约定：R_AB 将 B 系分量转换为 A 系分量。
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        x, y = point_m
        return [c * x - s * y, s * x + c * y]

    def apply2(angle_rad, translation_m, point_m):
        return [a + b for a, b in zip(rotate2(angle_rad, point_m), translation_m)]

    def quaternion_product(left, right):
        # 所有参数与返回值都严格采用 ROS 消息的 (x,y,z,w) 次序。
        # 乘法不交换；先应用 right，再应用 left 对应 left*right。
        x, y, z, w = left
        a, b, c, d = right
        return [w*a + x*d + y*c - z*b, w*b - x*c + y*d + z*a,
                w*c + x*b - y*a + z*d, w*d - x*a - y*b - z*c]

    # 平面实验：B 原点在 A 中为 (1,2)m，B 相对 A 绕 z 正转 90 度。
    angle = math.pi / 2.0
    translation = [1.0, 2.0]
    point_b = [2.0, 0.0]
    point_a = apply2(angle, translation, point_b)
    assert all(math.isclose(a, b, abs_tol=1e-12) for a, b in zip(point_a, [1.0, 4.0]))
    inverse_translation = rotate2(-angle, [-x for x in translation])
    recovered = apply2(-angle, inverse_translation, point_a)
    assert max(abs(a-b) for a, b in zip(recovered, point_b)) < 1e-12
    # 串联 A<-B<-C：不能直接把不同坐标系中的平移向量相加。
    t_bc = [0.5, 0.0]
    t_ac = apply2(angle, translation, t_bc)
    direct = apply2(angle + 0.2, t_ac, [0.3, -0.1])
    chained = apply2(angle, translation, apply2(0.2, t_bc, [0.3, -0.1]))
    assert max(abs(a-b) for a, b in zip(direct, chained)) < 1e-12

    # Rodrigues：本例单位旋转轴是 z，K=[u]_x；验证正交性与指定点的旋转。
    unit_axis = [0.0, 0.0, 1.0]
    k = [[0.0, -unit_axis[2], unit_axis[1]],
         [unit_axis[2], 0.0, -unit_axis[0]], [-unit_axis[1], unit_axis[0], 0.0]]
    k2 = [[sum(k[i][n] * k[n][j] for n in range(3)) for j in range(3)] for i in range(3)]
    rotation = [[float(i == j) + math.sin(angle)*k[i][j] + (1-math.cos(angle))*k2[i][j]
                 for j in range(3)] for i in range(3)]
    for i in range(3):
        for j in range(3):
            assert abs(sum(rotation[n][i]*rotation[n][j] for n in range(3)) - float(i == j)) < 1e-12
    assert abs(rotation[0][0]) < 1e-12 and math.isclose(rotation[1][0], 1.0, abs_tol=1e-12)

    # 单位四元数与其共轭相乘得到恒等旋转；零四元数不允许归一化。
    q = [0.0, 0.0, math.sin(angle/2.0), math.cos(angle/2.0)]
    assert math.isclose(sum(x*x for x in q), 1.0, abs_tol=1e-12)
    inverse_q = [-q[0], -q[1], -q[2], q[3]]
    identity_q = quaternion_product(q, inverse_q)
    assert max(abs(a-b) for a, b in zip(identity_q, [0, 0, 0, 1])) < 1e-12
    # q 与 -q 的二次旋转表达式一致；符号不同不代表姿态突变。
    yaw_cos_q = 1.0 - 2.0 * q[2]**2
    yaw_cos_minus_q = 1.0 - 2.0 * (-q[2])**2
    assert yaw_cos_q == yaw_cos_minus_q
    # 用纯向量四元数再次计算旋转，与 Rodrigues 的第一列独立对照。
    rotated_vector = quaternion_product(quaternion_product(q, [1.0, 0.0, 0.0, 0.0]), inverse_q)[:3]
    negative_q = [-value for value in q]
    negative_inverse = [-value for value in inverse_q]
    rotated_negative = quaternion_product(
        quaternion_product(negative_q, [1.0, 0.0, 0.0, 0.0]), negative_inverse)[:3]
    assert max(abs(rotated_vector[i]-rotation[i][0]) for i in range(3)) < 1e-12
    assert max(abs(a-b) for a, b in zip(rotated_vector, rotated_negative)) < 1e-12
    result = {'point_in_A_m': point_a, 'recovered_in_B_m': recovered, 'quaternion_xyzw': q}
    print('刚体变换实验通过：', result)
    return result

def lab_probability():
    import math
    import random

    def binary_posterior(prior, hit_rate, false_alarm):
        # 三个输入都是 [0,1] 内的无量纲概率；分母为零表示事件不可能发生。
        if not all(0.0 <= p <= 1.0 for p in (prior, hit_rate, false_alarm)):
            raise ValueError('概率必须在 [0,1] 内')
        evidence = prior * hit_rate + (1.0-prior) * false_alarm
        if evidence <= 0.0:
            raise ValueError('观测事件概率为零，不能条件化')
        return prior * hit_rate / evidence

    posterior = binary_posterior(0.2, 0.9, 0.1)
    assert math.isclose(posterior, 9.0/13.0, abs_tol=1e-12)
    try:
        binary_posterior(0.5, 0.0, 0.0)
    except ValueError:
        pass
    else:
        raise AssertionError('零证据事件本应被拒绝')

    # 两个传感器独立观测同一静止位置：米、平方米；采用平坦先验。
    measurements_m = [2.0, 2.6]
    variances_m2 = [0.04, 0.16]
    precisions = [1.0/value for value in variances_m2]
    posterior_variance = 1.0 / sum(precisions)
    posterior_mean = posterior_variance * sum(z*w for z, w in zip(measurements_m, precisions))
    assert math.isclose(posterior_mean, 2.12, abs_tol=1e-12)
    assert math.isclose(posterior_variance, 0.032, abs_tol=1e-12)

    # 有限样本计算证明：零协方差不蕴含独立。Y=X^2 完全由 X 决定。
    x_values = [-1.0, 0.0, 1.0]
    y_values = [x*x for x in x_values]
    mean_x, mean_y = sum(x_values)/3.0, sum(y_values)/3.0
    covariance = sum((x-mean_x)*(y-mean_y) for x, y in zip(x_values, y_values))/3.0
    assert math.isclose(covariance, 0.0, abs_tol=1e-12)
    assert y_values[1] == 0.0 and y_values[0] == 1.0

    # 固定随机种子，使采样实验可复现；容差是该固定样本的验收界限。
    # 不能把一次采样通过解释成分布、独立性或传感器质量的证明。
    generator = random.Random(20261107)
    samples = [generator.gauss(2.0, 0.2) for _ in range(30000)]
    sample_mean = sum(samples)/len(samples)
    sample_variance = sum((v-sample_mean)**2 for v in samples)/(len(samples)-1)
    assert abs(sample_mean-2.0) < 0.01
    assert abs(sample_variance-0.04) < 0.002
    result = {'posterior_inside': posterior, 'fused_position_m': posterior_mean,
              'fused_variance_m2': posterior_variance, 'sample_mean_m': sample_mean,
              'sample_variance_m2': sample_variance}
    print('概率与测量实验通过：', result)
    return result

def lab_estimation():
    import math

    def transpose(a):
        return [list(row) for row in zip(*a)]

    def multiply(a, b):
        # 只用于本例的小矩阵；尺寸必须满足 A 的列数等于 B 的行数。
        assert len(a[0]) == len(b)
        return [[sum(x*y for x, y in zip(row, column)) for column in zip(*b)] for row in a]

    def add(a, b):
        return [[x+y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]

    # x=[位置(m),速度(m/s)]；dt 单位 s；一次采样内未知加速度恒定。
    dt = 1.0
    state = [0.0, 1.0]
    covariance = [[0.04, 0.0], [0.0, 0.01]]
    transition = [[1.0, dt], [0.0, 1.0]]
    sigma_acceleration = 0.1  # m/s^2；这不是连续白噪声的谱密度。
    input_column = [0.5*dt*dt, dt]
    process_covariance = [[sigma_acceleration**2*a*b for b in input_column] for a in input_column]
    predicted_state = [state[0]+dt*state[1], state[1]]
    predicted_covariance = add(multiply(multiply(transition, covariance), transpose(transition)),
                               process_covariance)
    assert math.isclose(predicted_covariance[0][0], 0.0525, abs_tol=1e-12)

    # H=[1,0] 只测位置；R 必须是方差 m^2，不能误填标准差 0.2m。
    measured_position, measurement_variance = 1.2, 0.04
    innovation = measured_position-predicted_state[0]
    innovation_variance = predicted_covariance[0][0]+measurement_variance
    assert innovation_variance > 0.0
    gain = [predicted_covariance[i][0]/innovation_variance for i in range(2)]
    corrected_state = [x+k*innovation for x, k in zip(predicted_state, gain)]

    # Joseph 形式：P+=(I-KH)P-(I-KH)^T+KRK^T，较直接减法更便于保留正定性。
    identity_minus_kh = [[1.0-gain[0], 0.0], [-gain[1], 1.0]]
    corrected_covariance = add(
        multiply(multiply(identity_minus_kh, predicted_covariance), transpose(identity_minus_kh)),
        [[measurement_variance*a*b for b in gain] for a in gain])
    simplified = multiply(identity_minus_kh, predicted_covariance)
    assert max(abs(a-b) for ra, rb in zip(corrected_covariance, simplified) for a, b in zip(ra, rb)) < 1e-12
    assert abs(corrected_covariance[0][1]-corrected_covariance[1][0]) < 1e-12
    assert corrected_covariance[0][0]*corrected_covariance[1][1]-corrected_covariance[0][1]**2 > 0.0
    assert math.isclose(corrected_state[0], 1.1135135135135135, abs_tol=1e-12)
    # 同一个位置后验也能通过“先验精度+测量精度”计算，独立核对位置分量。
    scalar_variance = 1.0/(1.0/predicted_covariance[0][0]+1.0/measurement_variance)
    scalar_mean = scalar_variance*(predicted_state[0]/predicted_covariance[0][0]
                                   + measured_position/measurement_variance)
    assert math.isclose(corrected_state[0], scalar_mean, abs_tol=1e-12)

    # 无量纲 NIS：一维正确线性高斯模型下，门限 9 对应约三倍标准差。
    nis = innovation**2/innovation_variance
    outlier_nis = (100.0-predicted_state[0])**2/innovation_variance
    assert nis < 9.0 and outlier_nis > 9.0
    # 两次位置测量的可观性矩阵 [[1,0],[1,dt]] 在 dt!=0 时满秩。
    assert dt != 0.0
    result = {'predicted_state': predicted_state, 'gain': gain, 'corrected_state': corrected_state,
              'corrected_covariance': corrected_covariance, 'NIS': nis}
    print('状态估计实验通过：', result)
    return result

def lab_optimization():
    import math

    def residual(x):
        return x*x-4.0  # 教学无量纲残差，正根为 2，负根为 -2。

    def objective(x):
        return 0.5*residual(x)**2

    # 用中心差分独立核对解析梯度；h 是无量纲状态扰动。
    point, h = 1.3, 1e-6
    numerical_gradient = (objective(point+h)-objective(point-h))/(2*h)
    analytical_gradient = 2*point*residual(point)
    assert abs(numerical_gradient-analytical_gradient) < 1e-6

    # 一维 LM 风格演示：先提候选步，再用真实目标值决定接受与否。
    # 实际求解器通常使用更完整的信赖域增益比和尺度处理。
    x, damping = 1.0, 0.1
    accepted_costs = [objective(x)]
    for _ in range(60):
        r, jacobian = residual(x), 2*x
        if abs(r) < 1e-10:
            break
        delta = -jacobian*r/(jacobian*jacobian+damping)
        candidate = min(5.0, max(0.1, x+delta))  # 显式选择正根分支的状态范围。
        if objective(candidate) < objective(x):
            x = candidate
            damping = max(1e-12, damping/3.0)
            accepted_costs.append(objective(x))
        else:
            damping *= 10.0
    assert abs(x-2.0) < 1e-8
    assert all(a > b for a, b in zip(accepted_costs, accepted_costs[1:]))
    # x=0 的梯度为零，增加阻尼并不能自动摆脱这个非最优驻点。
    assert 2*0.0*residual(0.0) == 0.0 and objective(0.0) > objective(2.0)

    # 投影梯度：最小化 0.5*(x-3)^2，约束 [-1,1]；最优点位于上边界。
    constrained = 0.0
    for _ in range(30):
        constrained = min(1.0, max(-1.0, constrained-0.5*(constrained-3.0)))
    assert constrained == 1.0
    multiplier = 3.0-constrained
    assert math.isclose((constrained-3.0)+multiplier, 0.0, abs_tol=1e-12)

    # Huber 损失：delta=1m；这里已把测量按 1m 参考尺度无量纲化。
    measurements = [2.0, 2.1, 1.9, 20.0]
    ordinary_mean = sum(measurements)/len(measurements)
    robust = 2.0
    for _ in range(150):
        gradient = sum(max(-1.0, min(1.0, robust-z)) for z in measurements)
        robust -= 0.2*gradient
    assert math.isclose(robust, 7.0/3.0, abs_tol=1e-8)
    assert ordinary_mean == 6.5 and abs(robust-2.0) < abs(ordinary_mean-2.0)
    result = {'nonlinear_positive_root': x, 'accepted_costs': accepted_costs,
              'constrained_solution': constrained, 'L2_mean': ordinary_mean, 'Huber_estimate': robust}
    print('优化实验通过：', result)
    return result

def lab_kinematics():
    import math
    length_1, length_2 = 0.6, 0.4  # 两个刚性杆的长度，单位 m。

    def forward(q):
        a, b = q
        return [length_1*math.cos(a)+length_2*math.cos(a+b),
                length_1*math.sin(a)+length_2*math.sin(a+b)]

    def jacobian(q):
        a, b = q
        return [[-length_1*math.sin(a)-length_2*math.sin(a+b), -length_2*math.sin(a+b)],
                [length_1*math.cos(a)+length_2*math.cos(a+b), length_2*math.cos(a+b)]]

    def inverse(point, elbow_sign):
        # elbow_sign 为 +1 或 -1，显式选择肘部两种支路；越界目标必须拒绝。
        px, py = point
        cosine = (px*px+py*py-length_1**2-length_2**2)/(2*length_1*length_2)
        if cosine < -1.0-1e-12 or cosine > 1.0+1e-12:
            raise ValueError('目标不在两连杆可达环带内')
        # 仅钳位浮点舍入误差，不能把真实越界目标投射成可达目标。
        q2 = elbow_sign*math.acos(min(1.0, max(-1.0, cosine)))
        q1 = math.atan2(py, px)-math.atan2(length_2*math.sin(q2), length_1+length_2*math.cos(q2))
        return [q1, q2]

    q = [math.pi/6.0, -math.pi/3.0]
    position = forward(q)
    j = jacobian(q)
    step = 1e-6  # 雅可比差分的角度扰动，单位 rad。
    for joint in range(2):
        plus, minus = q.copy(), q.copy()
        plus[joint] += step
        minus[joint] -= step
        numerical = [(a-b)/(2*step) for a, b in zip(forward(plus), forward(minus))]
        assert max(abs(numerical[i]-j[i][joint]) for i in range(2)) < 1e-8
    recovered = inverse(position, -1)
    assert max(abs(a-b) for a, b in zip(recovered, q)) < 1e-12
    for branch in (-1, 1):
        p = forward(inverse(position, branch))
        assert max(abs(a-b) for a, b in zip(p, position)) < 1e-12
    try:
        inverse([2.0, 0.0], 1)
    except ValueError:
        pass
    else:
        raise AssertionError('不可达点本应被拒绝')

    # J 的单位 m/rad；qdot 单位 rad/s，因此末端速度单位 m/s。
    rates = [0.2, -0.1]
    velocity = [sum(a*b for a, b in zip(row, rates)) for row in j]
    force = [2.0, 3.0]  # 在同一个基坐标系表达的末端力，单位 N。
    torque = [sum(j[i][k]*force[i] for i in range(2)) for k in range(2)]
    # 虚功/功率一致性：tau^T*qdot 与 F^T*pdot 均为 W。
    power_joint = sum(a*b for a, b in zip(torque, rates))
    power_tip = sum(a*b for a, b in zip(force, velocity))
    assert math.isclose(power_joint, power_tip, abs_tol=1e-12)
    determinant = j[0][0]*j[1][1]-j[0][1]*j[1][0]
    assert math.isclose(determinant, length_1*length_2*math.sin(q[1]), abs_tol=1e-12)
    straight = jacobian([0.3, 0.0])
    assert abs(straight[0][0]*straight[1][1]-straight[0][1]*straight[1][0]) < 1e-12
    result = {'tip_position_m': position, 'tip_velocity_m_s': velocity,
              'joint_torque_Nm': torque, 'power_W': power_tip}
    print('运动学实验通过：', result)
    return result

def lab_dynamics():
    import math
    mass, length, gravity = 2.0, 0.5, 9.81  # kg、m、m/s^2；杆无质量，质点在杆端。
    inertia = mass*length*length  # 转轴惯量 kg*m^2，不是质心处惯量。
    dt = 0.005  # 固定积分步长 s；本实验不含接触碰撞或执行器延迟。

    def derivative(state, viscous, torque):
        angle, rate = state
        # angle 自竖直向下方向计量(rad)，rate 单位 rad/s。
        acceleration = (torque-viscous*rate-mass*gravity*length*math.sin(angle))/inertia
        return [rate, acceleration]

    def rk4(state, viscous, torque):
        # 四阶 Runge-Kutta 是数值近似，不是严格的保能积分器。
        k1 = derivative(state, viscous, torque)
        k2 = derivative([x+dt*k/2 for x, k in zip(state, k1)], viscous, torque)
        k3 = derivative([x+dt*k/2 for x, k in zip(state, k2)], viscous, torque)
        k4 = derivative([x+dt*k for x, k in zip(state, k3)], viscous, torque)
        return [x+dt*(a+2*b+2*c+d)/6 for x, a, b, c, d in zip(state, k1, k2, k3, k4)]

    def energy(state):
        angle, rate = state
        return 0.5*inertia*rate*rate+mass*gravity*length*(1-math.cos(angle))  # J

    initial = [0.7, 0.0]
    conservative = initial.copy()
    initial_energy = energy(initial)
    for _ in range(2000):
        conservative = rk4(conservative, 0.0, 0.0)
    drift = abs(energy(conservative)-initial_energy)
    assert drift < 1e-6

    dissipative, previous_energy = initial.copy(), initial_energy
    for _ in range(2000):
        dissipative = rk4(dissipative, 0.2, 0.0)  # b 单位 N*m*s/rad。
        next_energy = energy(dissipative)
        assert next_energy <= previous_energy+1e-10
        previous_energy = next_energy
    assert energy(dissipative) < initial_energy

    # 静态平衡需要 tau=m*g*l*sin(theta)；并非所有姿态都能由限幅电机保持。
    held_angle = 0.3
    holding_torque = mass*gravity*length*math.sin(held_angle)
    assert abs(derivative([held_angle, 0.0], 0.2, holding_torque)[1]) < 1e-12
    # 能量导数 dE/dt=omega*(tau-b*omega)，用状态导数验证同一等式。
    state, b, tau = [0.3, 0.1], 0.2, 0.5
    speed, acceleration = derivative(state, b, tau)
    chain_rule = inertia*state[1]*acceleration+mass*gravity*length*math.sin(state[0])*speed
    assert math.isclose(chain_rule, state[1]*(tau-b*state[1]), abs_tol=1e-12)

    # 两个杆端质点的平面 2R 质量矩阵，验证动力学正定性与运动学奇异的区别。
    l1, l2, m1, m2 = 0.6, 0.4, 1.0, 0.5
    for q2 in (0.0, 0.4, math.pi):
        a = m1*l1*l1+m2*(l1*l1+l2*l2+2*l1*l2*math.cos(q2))
        b12 = m2*(l2*l2+l1*l2*math.cos(q2))
        d = m2*l2*l2
        assert a > 0.0 and a*d-b12*b12 > 0.0
    result = {'initial_energy_J': initial_energy, 'conservative_drift_J': drift,
              'dissipative_final_energy_J': energy(dissipative), 'holding_torque_Nm': holding_torque}
    print('动力学实验通过：', result)
    return result

def lab_control():
    import math

    def discrete_integrator(initial_error_m, gain_per_s, period_s, steps, limit_m_s=None):
        if gain_per_s <= 0.0 or period_s <= 0.0:
            raise ValueError('增益和采样周期必须为正')
        error = initial_error_m
        history = [error]
        for _ in range(steps):
            velocity = -gain_per_s*error  # P 控制输出的单位为 m/s。
            if limit_m_s is not None:
                velocity = max(-limit_m_s, min(limit_m_s, velocity))
            error += period_s*velocity  # 本例被控对象是理想位置积分器。
            history.append(error)
        return history

    # 离散闭环乘子为 1-k*dt；连续时间 k>0 并不足以保证离散实现稳定。
    stable = discrete_integrator(1.0, 2.0, 0.1, 100)
    unstable = discrete_integrator(1.0, 3.0, 1.0, 10)
    assert abs(stable[-1]) < 1e-8
    assert abs(unstable[-1]) == 1024.0
    saturated = discrete_integrator(2.0, 2.0, 0.1, 200, limit_m_s=0.3)
    assert abs(saturated[-1]) < 1e-8
    assert max(abs(b-a) for a, b in zip(saturated, saturated[1:])) <= 0.030000000001

    # 力控质点：m*xddot=u-c*xdot；u=-kp*x-kd*xdot，目标位置固定为 0m。
    mass, physical_damping = 2.0, 0.4  # kg、N*s/m。
    kp, kd = 4.0, 3.6  # N/m、N*s/m；闭环总阻尼为 4.0 N*s/m。
    dt = 0.005
    state = [1.0, 0.0]  # [位置误差(m), 速度(m/s)]。

    def derivative(value):
        error, speed = value
        return [speed, (-kp*error-(physical_damping+kd)*speed)/mass]

    def lyapunov(value):
        error, speed = value
        return 0.5*kp*error*error+0.5*mass*speed*speed  # J。

    previous_energy = lyapunov(state)
    for _ in range(3000):
        # RK4 仅用于近似连续对象，不能据此证明真实机器人闭环稳定。
        k1 = derivative(state)
        k2 = derivative([x+dt*k/2 for x, k in zip(state, k1)])
        k3 = derivative([x+dt*k/2 for x, k in zip(state, k2)])
        k4 = derivative([x+dt*k for x, k in zip(state, k3)])
        state = [x+dt*(a+2*b+2*c+d)/6 for x, a, b, c, d in zip(state, k1, k2, k3, k4)]
        current_energy = lyapunov(state)
        assert current_energy <= previous_energy+1e-10
        previous_energy = current_energy
    assert abs(state[0]) < 1e-5 and abs(state[1]) < 1e-5
    damping_ratio = (physical_damping+kd)/(2*math.sqrt(mass*kp))
    assert math.isclose(damping_ratio, 1/math.sqrt(2), abs_tol=1e-12)
    result = {'stable_error_m': stable[-1], 'unstable_error_m': unstable[-1],
              'saturated_error_m': saturated[-1], 'PD_final_state': state,
              'PD_damping_ratio': damping_ratio}
    print('反馈控制实验通过：', result)
    return result


def main():
    """选择并运行章节；assert失败会保留非零退出码，便于自动验收。"""
    import argparse
    import json
    experiments = {
        'math-linear': lab_linear,
        'math-rigid': lab_rigid,
        'math-probability': lab_probability,
        'math-estimation': lab_estimation,
        'math-optimization': lab_optimization,
        'math-kinematics': lab_kinematics,
        'math-dynamics': lab_dynamics,
        'math-control': lab_control,
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chapter', choices=experiments, help='省略时依次运行全部八章')
    args = parser.parse_args()
    selected = [args.chapter] if args.chapter else list(experiments)
    results = {identifier: experiments[identifier]() for identifier in selected}
    print(json.dumps({'passed': True, 'chapters': len(results), 'results': results}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
