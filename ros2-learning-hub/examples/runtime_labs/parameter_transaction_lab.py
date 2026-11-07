#!/usr/bin/env python3
"""Jazzy 参数 pre/on/post、完整候选配置与逐项/原子提交的进程内实验。

数据：lower_m、upper_m 是合成位置允许区间的下/上限，单位米；要求 -100≤lower<upper≤100。
span_m 是 pre 推导的 upper-lower，单位米。所有参数为有限 DOUBLE，不控制硬件或文件资源。
顺序：pre 返回改写后的列表；on 只校验合并候选；参数存储提交后 post 更新不可变内存快照。
包含故意错误的 on 副作用、post 返回拒绝值和 post 抛异常，均仅污染本例内存以展示边界。
运行：source /opt/ros/jazzy/setup.bash 后 python3 examples/runtime_labs/parameter_transaction_lab.py。
--help 不导入 ROS；--json 输出完整结果。禁止 -O/PYTHONOPTIMIZE 绕过断言。

所有设置直接调用同进程 Node API，不启动执行器或参数服务，不发送参数服务请求。
真实 rclpy Node 仍会创建 RMW 资源及默认 /parameter_events 发布器；不能称为零 DDS 端点。
本例将本进程发现范围设为 OFF，默认独立域223；关闭 rosout 与参数服务，不连接机器人。
"""

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import gc
import json
import math
import os
import sys
import weakref


@dataclass(frozen=True)
class Limits:
    """业务使用的完整不可变内存快照；三个字段均以米计，不代表硬件状态。"""
    lower_m: float
    upper_m: float
    span_m: float


def run_lab(domain_id=223):
    # 只影响当前实验进程，不改系统配置。关闭自动发现以避免接触同机其他 ROS 应用。
    # RMW 初始化可能仍打开本地传输资源；它不是“完全没有网络实现”的承诺。
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'OFF'
    os.environ.pop('ROS_STATIC_PEERS', None)
    os.environ.pop('ROS_LOCALHOST_ONLY', None)
    from rcl_interfaces.msg import SetParametersResult
    from rclpy.context import Context
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.utilities import get_rmw_implementation_identifier

    fields = ('lower_m', 'upper_m', 'span_m')
    initial = dict(lower_m=0.0, upper_m=1.0, span_m=1.0)
    results, created, destroyed = [], [], []

    def safe_value(value):
        # JSON 不输出非标准 NaN/Infinity；非法输入仍按字符串明确记录，参数不会被接纳。
        if isinstance(value, float) and not math.isfinite(value):
            return repr(value)
        if isinstance(value, dict):
            return {k: safe_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [safe_value(v) for v in value]
        return value

    def describe(parameters):
        return [dict(name=p.name, type=p.type_.name, value=safe_value(p.value)) for p in parameters]

    def params(lower=None, upper=None):
        """构造本例输入；None 表示本次不更新该字段，不能用0代替“未提供”。"""
        out = []
        if lower is not None:
            out.append(Parameter('lower_m', value=lower))
        if upper is not None:
            out.append(Parameter('upper_m', value=upper))
        return out

    def outcome(result):
        return dict(successful=result.successful, reason=result.reason)

    class ControlledPostFailure(RuntimeError):
        """只在反例中触发的已提交后应用失败，不表示自动撤销参数存储。"""

    class LabNode(Node):
        def __init__(self, context, name, mode='correct'):
            super().__init__(name, context=context,
                             namespace=f'/parameter_transaction_{os.getpid()}',
                             enable_rosout=False, start_parameter_services=False,
                             use_global_arguments=False)
            # 先声明 DOUBLE 默认值，后注册实验回调，避免把声明时的 on/post 混入设置阶段。
            self.declare_parameters('', [(name, value) for name, value in initial.items()])
            self.events = []
            self.snapshot = Limits(**initial)
            self.application_state = 'ready'
            self.pre_ref = self.pre
            self.validate_ref = self.validate
            self.post_ref = self.post_commit
            self.registration_returns = []
            self.registration_returns.append(self.add_pre_set_parameters_callback(self.pre_ref))
            if mode in ('bad_on', 'good_veto'):
                # Jazzy 新注册的 on 回调先运行。先注册“最后拒绝者”，再注册前面的校验者。
                self.registration_returns.append(self.add_on_set_parameters_callback(self.late_reject))
                callback = self.bad_on if mode == 'bad_on' else self.validate_ref
                self.registration_returns.append(self.add_on_set_parameters_callback(callback))
            else:
                self.registration_returns.append(self.add_on_set_parameters_callback(self.validate_ref))
            if mode == 'post_false':
                self.post_ref = self.post_false
            elif mode == 'post_raises':
                self.post_ref = self.post_raises
            self.registration_returns.append(self.add_post_set_parameters_callback(self.post_ref))
            # Python 注册函数返回 None；Node 自己保留 callable，不能照搬 C++ SharedPtr 句柄。
            assert all(value is None for value in self.registration_returns)

        def store(self):
            """只用公开 get_parameter 读取完整当前配置；不把旧缓存冒充真实参数存储。"""
            return {name: self.get_parameter(name).value for name in fields}

        def candidate(self, parameters):
            # 合并是关键：本次可能只有 upper_m，未提交的 lower_m 必须保留当前值。
            proposed = self.store()
            for item in parameters:
                if item.name in proposed:
                    proposed[item.name] = item.value
            return proposed

        def trace(self, stage, **details):
            # 跟踪日志只是教学观测，不能作为参数提交确认，不修改业务快照或外部资源。
            self.events.append(safe_value(dict(stage=stage, **details)))

        def pre(self, parameters):
            # Python pre 必须返回 List[Parameter]。本例只有一个 pre；返回新列表，不修改原请求。
            forwarded = list(parameters)
            proposed = self.candidate(parameters)
            touches_bounds = any(p.name in ('lower_m', 'upper_m') for p in parameters)
            lower, upper = proposed['lower_m'], proposed['upper_m']
            finite_double = all(type(v) is float and math.isfinite(v) for v in (lower, upper))
            if touches_bounds and finite_double and all(abs(v) <= 100.0 for v in (lower, upper)):
                # span_m 是派生参数：涉及上下限时统一重算；不能凭旧span校验新上下限。
                # 此处不决定接纳，lower>=upper 的负宽度仍会交由 on 拒绝。
                forwarded = [p for p in forwarded if p.name != 'span_m']
                forwarded.append(Parameter('span_m', value=upper - lower))
            self.trace('pre', received=describe(parameters), forwarded=describe(forwarded),
                       store_before=self.store())
            return forwarded

        def validate(self, parameters, stage='on_validate'):
            proposed = self.candidate(parameters)
            self.trace(stage, candidate=proposed, store_before=self.store(),
                       snapshot_before=asdict(self.snapshot))
            # 类型通常先被静态 DOUBLE 描述符拒绝；这里仍为完整候选写出明确业务合同。
            if not all(type(v) is float and math.isfinite(v) for v in proposed.values()):
                return SetParametersResult(successful=False, reason='all fields require finite DOUBLE metres')
            lower, upper, span = (proposed[name] for name in fields)
            if not (-100.0 <= lower < upper <= 100.0):
                return SetParametersResult(successful=False, reason='require -100 <= lower_m < upper_m <= 100')
            if not math.isclose(span, upper - lower, rel_tol=0.0, abs_tol=1.0e-12):
                return SetParametersResult(successful=False, reason='span_m must equal upper_m-lower_m')
            # 不在 on 中重建对象、切换业务缓存或递归 set/declare；后面的校验者仍可能拒绝。
            return SetParametersResult(successful=True)

        def late_reject(self, parameters):
            self.trace('on_late_reject', request=describe(parameters), store_before=self.store())
            return SetParametersResult(successful=False, reason='deliberate second-validator veto')

        def bad_on(self, parameters):
            accepted = self.validate(parameters, stage='on_bad_validate')
            if accepted.successful:
                # 故意错误的反例：另一个校验者尚未运行，业务缓存却已提前改变。
                self.snapshot = Limits(**self.candidate(parameters))
                self.trace('on_bad_cache_write', polluted_snapshot=asdict(self.snapshot))
            return accepted

        def post_commit(self, _parameters):
            # 到达 post 时参数存储已经提交。重新读取完整存储，再一次替换不可变快照。
            # 这只演示单线程内存应用动作，不提供跨线程锁、硬件事务或失败回滚。
            before = asdict(self.snapshot)
            committed = self.store()
            self.snapshot = Limits(**committed)
            self.application_state = 'ready'
            self.trace('post_commit', committed_store=committed,
                       snapshot_before=before, snapshot_after=asdict(self.snapshot))

        def post_false(self, parameters):
            self.post_commit(parameters)
            self.trace('post_attempted_veto', detail='错误返回值；公开post合同应返回None')
            # 故意违反返回约定的反例：Jazzy 忽略 post 返回值，它不是第二个 on 校验者。
            return SetParametersResult(successful=False, reason='post cannot veto committed parameters')

        def post_raises(self, _parameters):
            self.application_state = 'apply_failed'
            self.trace('post_failure', committed_store=self.store(),
                       unchanged_snapshot=asdict(self.snapshot))
            # 仅模拟内存应用失败；调用者会收到异常，但存储不因此自动回滚。
            raise ControlledPostFailure('deliberate failure after parameter-store commit')

    context = Context()
    # 禁用自动文件日志初始化，避免教学实验写用户目录；真实 Context 仍初始化 RMW。
    context.init(args=[], initialize_logging=False, domain_id=domain_id)
    rmw = get_rmw_implementation_identifier()

    @contextmanager
    def fresh(mode='correct'):
        name = f'parameter_case_{len(created) + 1}'
        node = LabNode(context, name, mode)
        created.append(node.get_fully_qualified_name())
        try:
            yield node
        finally:
            full_name = node.get_fully_qualified_name()
            node.destroy_node()
            destroyed.append(full_name)

    def state(node):
        return dict(store=node.store(), snapshot=asdict(node.snapshot),
                    application_state=node.application_state)

    def phases(node):
        return [event['stage'] for event in node.events]

    try:
        with fresh() as node:
            original_request = params(2.0, 3.0)
            result = node.set_parameters_atomically(original_request)
            expected = dict(lower_m=2.0, upper_m=3.0, span_m=1.0)
            assert result.successful and node.store() == expected == asdict(node.snapshot)
            assert phases(node) == ['pre', 'on_validate', 'post_commit']
            assert len(original_request) == 2  # pre 返回新列表，原始请求没有被追加 span。
            assert node.events[1]['store_before'] == initial
            assert node.events[2]['committed_store'] == expected
            results.append(dict(id='legal_atomic_pre_on_post', passed=True,
                                expected=expected, actual=state(node), result=outcome(result), events=list(node.events)))

        with fresh() as node:
            result = node.set_parameters_atomically(params(2.0, 1.0))
            assert not result.successful and node.store() == initial == asdict(node.snapshot)
            assert phases(node) == ['pre', 'on_validate']
            results.append(dict(id='invalid_cross_constraint_atomic_keeps_old', passed=True,
                                expected=initial, actual=state(node), result=outcome(result), events=list(node.events)))

        with fresh() as node:
            assert node.set_parameters_atomically(params(2.0, 3.0)).successful
            node.events.clear()
            result = node.set_parameters_atomically(params(upper=4.0))
            expected = dict(lower_m=2.0, upper_m=4.0, span_m=2.0)
            assert result.successful and node.store() == expected == asdict(node.snapshot)
            assert [p['name'] for p in node.events[0]['received']] == ['upper_m']
            results.append(dict(id='partial_update_merges_old_fields', passed=True,
                                expected=expected, actual=state(node), result=outcome(result), events=list(node.events)))

        invalid_results = []
        for case, value in [('integer', 1), ('boolean', True), ('string', '0.5'),
                            ('nan', float('nan')), ('positive_inf', float('inf')),
                            ('negative_inf', float('-inf')), ('finite_outside_range', 101.0)]:
            with fresh() as node:
                request = [Parameter('lower_m', value=value)]
                result = node.set_parameters_atomically(request)
                assert not result.successful and node.store() == initial == asdict(node.snapshot)
                assert 'post_commit' not in phases(node)
                invalid_results.append(dict(case=case, input=describe(request), result=outcome(result),
                                            expected_unchanged=initial, actual=state(node), events=list(node.events)))
        results.append(dict(id='type_nonfinite_and_range_rejections', passed=True, cases=invalid_results))

        comparison = {}
        for api in ('set_parameters', 'set_parameters_atomically'):
            with fresh() as node:
                returned = getattr(node, api)(params(2.0, 3.0))
                if api == 'set_parameters':
                    assert [r.successful for r in returned] == [False, True]
                    expected = dict(lower_m=0.0, upper_m=3.0, span_m=3.0)
                    returned_results = [outcome(r) for r in returned]
                else:
                    assert returned.successful
                    expected = dict(lower_m=2.0, upper_m=3.0, span_m=1.0)
                    returned_results = outcome(returned)
                assert node.store() == expected == asdict(node.snapshot)
                comparison[api] = dict(expected=expected, actual=state(node), result=returned_results,
                                       events=list(node.events))
        results.append(dict(id='sequential_partial_success_vs_atomic_batch', passed=True, comparison=comparison))

        veto_comparison = {}
        for mode in ('bad_on', 'good_veto'):
            with fresh(mode) as node:
                result = node.set_parameters_atomically(params(2.0, 3.0))
                expected_snapshot = dict(lower_m=2.0, upper_m=3.0, span_m=1.0) if mode == 'bad_on' else initial
                assert not result.successful and node.store() == initial
                assert asdict(node.snapshot) == expected_snapshot
                assert phases(node)[-1] == 'on_late_reject' and 'post_commit' not in phases(node)
                veto_comparison[mode] = dict(expected_store=initial, expected_snapshot=expected_snapshot,
                                             actual=state(node), result=outcome(result), events=list(node.events))
        results.append(dict(id='validator_side_effect_pollution_vs_pure_check', passed=True, comparison=veto_comparison))

        with fresh('post_false') as node:
            result = node.set_parameters_atomically(params(0.25, 0.75))
            expected = dict(lower_m=0.25, upper_m=0.75, span_m=0.5)
            assert result.successful and node.store() == expected == asdict(node.snapshot)
            assert phases(node)[-1] == 'post_attempted_veto'
            results.append(dict(id='post_return_false_cannot_veto', passed=True,
                                expected=expected, actual=state(node), result=outcome(result), events=list(node.events)))

        with fresh('post_raises') as node:
            try:
                node.set_parameters_atomically(params(0.25, 0.75))
            except ControlledPostFailure as error:
                message = str(error)
            else:
                raise AssertionError('受控post异常应传播给直接调用者')
            expected = dict(lower_m=0.25, upper_m=0.75, span_m=0.5)
            assert node.store() == expected and asdict(node.snapshot) == initial
            assert node.application_state == 'apply_failed'
            results.append(dict(id='post_exception_does_not_rollback_store', passed=True,
                                expected_store=expected, expected_snapshot=initial, actual=state(node),
                                raised='ControlledPostFailure', message=message, events=list(node.events)))

        with fresh() as node:
            observer_log = []

            class Observer:
                def __call__(self, _parameters):
                    observer_log.append('called')

            observer = Observer()
            observer_ref = weakref.ref(observer)
            registration = node.add_post_set_parameters_callback(observer)
            assert registration is None
            del observer
            gc.collect()
            assert observer_ref() is not None  # Node 保持强引用；不是C++弱句柄模型。
            assert node.set_parameters_atomically(params(0.25, 0.75)).successful
            assert observer_log == ['called']
            node.remove_post_set_parameters_callback(observer_ref())
            gc.collect()
            assert observer_ref() is None
            results.append(dict(id='python_callback_ownership_and_removal', passed=True,
                                expected=dict(registration=None, retained_until_remove=True, calls=1, released=True),
                                actual=dict(registration=registration, calls=len(observer_log), released=observer_ref() is None)))

        with fresh() as node:
            node.remove_pre_set_parameters_callback(node.pre_ref)

            def empty_pre(parameters):
                node.trace('pre_empty', received=describe(parameters))
                return []

            node.add_pre_set_parameters_callback(empty_pre)
            result = node.set_parameters_atomically(params(0.25, 0.75))
            assert not result.successful and node.store() == initial == asdict(node.snapshot)
            assert phases(node) == ['pre_empty']
            results.append(dict(id='empty_pre_list_rejected_before_on', passed=True,
                                expected=initial, actual=state(node), result=outcome(result), events=list(node.events)))

        with fresh() as node:
            node.remove_pre_set_parameters_callback(node.pre_ref)

            def wrong_void_pre(parameters):
                node.trace('pre_missing_return', received=describe(parameters))
                # 故意遗漏 return：不能把 C++ void(vector&) 风格直接照搬成 Python pre。

            node.add_pre_set_parameters_callback(wrong_void_pre)
            try:
                node.set_parameters_atomically(params(0.25, 0.75))
            except TypeError as error:
                message = str(error)
            else:
                raise AssertionError('Python pre不返回列表应失败')
            assert node.store() == initial == asdict(node.snapshot)
            assert phases(node) == ['pre_missing_return']
            results.append(dict(id='python_pre_requires_list_return', passed=True,
                                expected=initial, actual=state(node), raised='TypeError', message=message,
                                events=list(node.events)))
    finally:
        # 每个fresh节点在其finally中销毁；最后关闭专属Context，不触碰其他进程/上下文。
        if context.ok():
            context.shutdown()

    assert len(results) == 11 and all(item['passed'] for item in results)
    assert created == destroyed and not context.ok()
    return dict(
        lab='parameter_transaction_lab', passed=True, cases=len(results), results=results,
        units=dict(lower_m='m', upper_m='m', span_m='m', derived_relation='span_m=upper_m-lower_m'),
        comparison_absolute_tolerance_m=1.0e-12,
        runtime=dict(domain_id=domain_id, discovery_range='OFF', rmw=rmw,
                     parameter_services_started=False, rosout_enabled=False, executor_started=False,
                     parameter_calls='同进程公开Node API；没有DDS参数请求/应答',
                     framework_entities='真实Node仍初始化RMW并创建默认parameter_events发布器'),
        cleanup=dict(nodes_created=len(created), nodes_destroyed=len(destroyed),
                     all_node_names=created, destroyed_node_names=destroyed, context_shutdown=not context.ok()),
        cpp_python_contract=dict(
            python_pre='Callable[[List[Parameter]], List[Parameter]]；返回修改后的列表',
            cpp_pre='std::function<void(std::vector<rclcpp::Parameter>&)>；就地修改可变vector，返回void',
            on='两种语言均返回SetParametersResult；全部on通过才提交参数存储',
            post='Python返回None，C++返回void；存储提交后运行，不是撤销接口',
            python_registration='返回None；Node强引用callable；用同一个callable的remove_*注销',
            cpp_registration='返回SharedPtr回调句柄，必须保留；实现保存weak_ptr，句柄释放后失效',
            validation_boundary='Python行为已运行；C++签名/顺序/句柄仅核对固定Jazzy源码，未编译运行C++'),
        limits=['只演示单线程、本节点参数存储及内存快照，不提供跨节点/跨线程事务。',
                '参数原子设置不保证post成功，不涵盖硬件资源重配置、文件或网络副作用。',
                'pre/on/post中的业务副作用均无法靠参数拒绝或post异常自动撤销。'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='将完整结果作为一个JSON对象写到stdout')
    parser.add_argument('--domain-id', type=int, default=223, help='专属实验ROS域，0~232，默认223')
    args = parser.parse_args(argv)  # --help此时退出，尚未导入ROS。
    if not 0 <= args.domain_id <= 232:
        parser.error('domain-id必须在0~232内，选择没有其他应用使用的实验域')
    if not __debug__:
        print('本实验必须启用assert，不能使用-O/PYTHONOPTIMIZE。', file=sys.stderr)
        return 2
    try:
        result = run_lab(args.domain_id)
    except ImportError as error:
        print('缺少Jazzy依赖：请安装rclpy/rcl_interfaces并source /opt/ros/jazzy/setup.bash。' + str(error), file=sys.stderr)
        return 2
    except AssertionError as error:
        print('参数阶段断言失败：' + str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        for item in result['results']:
            print('通过 ' + item['id'] + ': ' + json.dumps(item, ensure_ascii=False, allow_nan=False))
        print(f"{result['cases']}组通过；{result['cleanup']['nodes_destroyed']}个节点已销毁，Context已关闭。仅验证软件内存参数行为。")
    return 0


if __name__ == '__main__':
    sys.exit(main())
