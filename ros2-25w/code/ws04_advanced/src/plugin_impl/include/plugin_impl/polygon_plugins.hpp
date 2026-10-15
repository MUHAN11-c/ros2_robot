/*
    需求：插件实现 —— 基于基类实现三角形与正方形插件，并注册到 pluginlib。
*/
#ifndef PLUGIN_IMPL__POLYGON_PLUGINS_HPP_
#define PLUGIN_IMPL__POLYGON_PLUGINS_HPP_

#include "plugin_base/polygon_base.hpp"
#include <cmath>

namespace polygon_plugins
{
// 三角形插件；
class Triangle: public polygon_base::RegularPolygon
{
public:
    void initialize(double side_length) override
    {
        side_length_ = side_length;
    }
    double area() override
    {
        return 0.5 * side_length_ * side_length_ * std::sin(60.0 * M_PI / 180.0);
    }
};

// 正方形插件；
class Square: public polygon_base::RegularPolygon
{
public:
    void initialize(double side_length) override
    {
        side_length_ = side_length;
    }
    double area() override
    {
        return side_length_ * side_length_;
    }
};

}  // namespace polygon_plugins

#endif  // PLUGIN_IMPL__POLYGON_PLUGINS_HPP_
