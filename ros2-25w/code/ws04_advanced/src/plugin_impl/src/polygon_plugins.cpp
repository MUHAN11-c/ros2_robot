#include "plugin_impl/polygon_plugins.hpp"
#include "plugin_base/polygon_base.hpp"
#include "pluginlib/class_list_macros.hpp"

// 将插件类注册到 pluginlib；
PLUGINLIB_EXPORT_CLASS(polygon_plugins::Triangle, polygon_base::RegularPolygon)
PLUGINLIB_EXPORT_CLASS(polygon_plugins::Square, polygon_base::RegularPolygon)
