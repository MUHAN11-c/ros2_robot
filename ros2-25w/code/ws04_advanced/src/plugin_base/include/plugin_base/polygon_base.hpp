/*
    需求：插件基类 —— 定义规则多边形(polygon)插件的基础接口。
    说明：加载方只依赖该基类头文件，不依赖具体插件实现。
*/
#ifndef PLUGIN_BASE__POLYGON_BASE_HPP_
#define PLUGIN_BASE__POLYGON_BASE_HPP_

namespace polygon_base
{
// 规则多边形基类；
class RegularPolygon
{
public:
    virtual void initialize(double side_length) = 0;
    virtual double area() = 0;
    virtual ~RegularPolygon(){}

protected:
    double side_length_;
};

}  // namespace polygon_base

#endif  // PLUGIN_BASE__POLYGON_BASE_HPP_
