"""Topic crosswalk: source index entries lead to the synthesized local textbook."""
import re

ZSC = {
 1:['architecture','migration'],2:['architecture','network'],3:['migration'],
 4:['architecture'],5:['executors','lifecycle','composition'],
 6:['pubsub','services','actions','qos'],7:['launch','parameters'],8:['tf2','eco-tf-frames'],
 9:['time-bag'],10:['eco-perception-pipeline'],11:['eco-slam-mapping','eco-state-estimation'],
 12:['eco-nav2-stack','eco-nav2-task-programming'],13:['eco-control-framework','eco-hardware-integration'],
 14:['eco-moveit-planning','eco-manipulation-tasks'],15:['performance'],
 16:['security','eco-data-observability'],17:['eco-gazebo-simulation'],18:['eco-multi-robot'],
 19:['eco-perception-pipeline','eco-accelerated-robotics'],20:['learning-rl'],
 21:['learning-embodied'],22:['learning-policy']}

def map_entry(entry):
    if entry['site']=='zsc':
        return ZSC[int(re.search(r'chapter(\d+)',entry['url']).group(1))]
    title=entry['title']
    match=re.match(r'(\d+)\.(\d+)',title)
    if not match:
        major=re.search(r'第(\d+)章',title)
        return {1:['architecture','installation','workspace'],2:['pubsub','services','actions','parameters'],3:['graph-cli','network','workspace'],4:['launch','time-bag'],5:['tf2'],6:['eco-model-rviz']}.get(int(major.group(1)) if major else 0,['architecture'])
    major,minor=map(int,match.groups())
    if major==1:return {1:['architecture'],2:['installation'],3:['workspace','pubsub'],4:['workspace'],5:['architecture','workspace'],6:['architecture']}.get(minor,['architecture'])
    if major==2:return {1:['interfaces'],2:['pubsub','interfaces'],3:['services','interfaces'],4:['actions','interfaces'],5:['parameters']}.get(minor,['pubsub','services','actions','parameters'])
    if major==3:
        if minor==8:
            for word,id in [('话题','pubsub'),('服务','services'),('动作','actions'),('参数','parameters')]:
                if word in title:return [id]
        return {1:['network'],2:['workspace'],3:['workspace'],4:['graph-cli','launch'],5:['graph-cli','launch'],6:['time-bag'],7:['graph-cli'],8:['pubsub','services','actions','parameters']}.get(minor,['graph-cli'])
    if major==4:return ['time-bag'] if minor==4 else ['launch','time-bag'] if minor>=5 else ['launch']
    if major==5:return ['tf2','eco-tf-frames']
    if major==6:return ['eco-model-rviz']
    raise ValueError('Unmapped source entry: '+title)
