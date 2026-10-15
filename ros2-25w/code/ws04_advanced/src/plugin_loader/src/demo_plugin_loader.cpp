/*
    需求：插件加载 —— 使用 pluginlib 动态加载三角形与正方形插件并计算面积。
    测试：ros2 run plugin_loader demo_plugin_loader
*/
// 1.包含头文件；
#include "plugin_base/polygon_base.hpp"
#include "pluginlib/class_loader.hpp"

int main(int argc, char ** argv)
{
    (void)argc;
    (void)argv;
    // 3-1.创建一个插件加载器(加载 plugin_base/RegularPolygon 的实现)；
    pluginlib::ClassLoader<polygon_base::RegularPolygon> poly_loader("plugin_base","polygon_base::RegularPolygon");

    try
    {
        // 3-2.加载插件(三角形)；
        std::shared_ptr<polygon_base::RegularPolygon> triangle =
            poly_loader.createSharedInstance("polygon_plugins/Triangle");
        triangle->initialize(10.0);
        printf("三角形面积: %.2f\n",triangle->area());

        // 3-3.加载插件(正方形)；
        std::shared_ptr<polygon_base::RegularPolygon> square =
            poly_loader.createSharedInstance("polygon_plugins/Square");
        square->initialize(10.0);
        printf("正方形面积: %.2f\n",square->area());
    }
    catch(pluginlib::PluginlibException & ex)
    {
        printf("插件加载异常:%s\n",ex.what());
    }

    return 0;
}
