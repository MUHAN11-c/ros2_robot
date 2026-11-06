"""Integration checks: real Jazzy nodes, isolated domain, no hardware."""
import os
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

PREFIX=Path(os.environ.get('ATLAS_INSTALL_PREFIX','/tmp/ros2-atlas-build/install'))
class CrossLanguageTest(unittest.TestCase):
    def service_exchange(self,server,client):
        env=dict(os.environ,ROS_DOMAIN_ID='197',ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',ROS_LOG_DIR='/tmp/ros2-atlas-test-logs')
        programs=[PREFIX/'lib'/server/'add_server',PREFIX/'lib'/client/'add_client']
        self.assertTrue(all(p.is_file() for p in programs),'服务教学程序尚未安装')
        process=subprocess.Popen([str(programs[0]),'--ros-args','-r','__ns:=/atlas'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=env,start_new_session=True)
        try:
            result=subprocess.run([str(programs[1]),'--ros-args','-r','__ns:=/atlas'],env=env,text=True,capture_output=True,timeout=12)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('SUM=12',result.stdout+result.stderr)
        finally:
            if process.poll() is None:os.killpg(process.pid,signal.SIGINT)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            process.stderr.close()
    def exchange(self,publisher,subscriber):
        env=dict(os.environ,ROS_DOMAIN_ID='197',ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',ROS_LOG_DIR='/tmp/ros2-atlas-test-logs')
        programs=[PREFIX/'lib'/subscriber/'listener',PREFIX/'lib'/publisher/'talker']
        self.assertTrue(all(p.is_file() for p in programs),'教学工程尚未构建或安装')
        processes=[]
        with tempfile.TemporaryFile(mode='w+') as output:
            try:
                for executable in programs:
                    processes.append(subprocess.Popen([str(executable),'--ros-args','-r','__ns:=/atlas'],stdout=output,stderr=output,env=env,start_new_session=True))
                deadline=time.monotonic()+12
                text=''
                while time.monotonic()<deadline:
                    time.sleep(.25);output.seek(0);text=output.read()
                    if 'RECEIVED ATLAS_MESSAGE' in text:break
                self.assertIn('RECEIVED ATLAS_MESSAGE',text)
            finally:
                for p in processes:
                    if p.poll() is None:os.killpg(p.pid,signal.SIGINT)
                for p in processes:
                    try:p.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    def test_cpp_to_python(self):self.exchange('atlas_cpp','atlas_py')
    def test_python_to_cpp(self):self.exchange('atlas_py','atlas_cpp')
    def test_cpp_service_python_client(self):self.service_exchange('atlas_cpp','atlas_py')
    def test_python_service_cpp_client(self):self.service_exchange('atlas_py','atlas_cpp')
    def test_launch_frontends(self):
        from launch.frontend import Parser
        from launch.launch_description_sources import PythonLaunchDescriptionSource
        folder=PREFIX/'share/atlas_cpp/launch'
        self.assertTrue(folder.exists(),'launch文件尚未安装')
        for ext in ('xml','yaml'):
            entity,parser=Parser.load(str(folder/f'demo.launch.{ext}'))
            description=parser.parse_description(entity)
            self.assertEqual(len(description.entities),2)
        from launch import LaunchContext
        description=PythonLaunchDescriptionSource(str(folder/'demo.launch.py')).get_launch_description(LaunchContext())
        self.assertEqual(len(description.entities),2)
if __name__=='__main__':unittest.main(verbosity=2)
