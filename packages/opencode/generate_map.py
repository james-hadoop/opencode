import folium
from folium.plugins import Fullscreen, MousePosition, MiniMap

m = folium.Map(location=[30.6580, 104.0658], zoom_start=13, tiles="OpenStreetMap")
m.add_child(MiniMap(toggle_preset=True))

title_html = '''
<div style="position: fixed; 
     top: 10px; left: 50px; width: 380px; 
     background-color: white; padding: 15px;
     border: 2px solid #3388ff; border-radius: 10px;
     z-index: 9999; font-family: Arial; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">
     <h4 style="margin:0; color: #333;">成都二环内综合地图</h4>
     <p style="margin:8px 0 0 0; font-size: 12px; color: #666;">
        景点 | 地铁 | 公交 | 酒店 | 主干道
     </p>
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

icon_colors = {
    "景点": "red", "地铁站": "blue", "公交站": "green", "酒店": "orange", "主干道路": "purple",
}

spots = [
    {"name": "宽窄巷子", "lat": 30.6740, "lng": 104.0569, "desc": "成都三大历史文化保护区之一"},
    {"name": "锦里", "lat": 30.6521, "lng": 104.0565, "desc": "武侯祠旁边的民俗商业街"},
    {"name": "武侯祠", "lat": 30.6515, "lng": 104.0539, "desc": "诸葛亮纪念馆"},
    {"name": "春熙路", "lat": 30.6582, "lng": 104.0644, "desc": "成都最繁华的商业步行街"},
    {"name": "太古里", "lat": 30.6545, "lng": 104.0695, "desc": "开放式街区式购物中心"},
    {"name": "大慈寺", "lat": 30.6570, "lng": 104.0692, "desc": "唐代古寺"},
    {"name": "文殊院", "lat": 30.6810, "lng": 104.0725, "desc": "长江流域四大禅林之一"},
    {"name": "人民公园", "lat": 30.6630, "lng": 104.0620, "desc": "成都最早的公园"},
    {"name": "天府广场", "lat": 30.6593, "lng": 104.0632, "desc": "成都城市几何中心"},
    {"name": "青羊宫", "lat": 30.6857, "lng": 104.0418, "desc": "川西第一道观"},
    {"name": "望江楼公园", "lat": 30.6466, "lng": 104.0729, "desc": "纪念唐代女诗人薛涛"},
    {"name": "成都博物馆", "lat": 30.6624, "lng": 104.0614, "desc": "成都最大综合性博物馆"},
    {"name": "四川科技馆", "lat": 30.6598, "lng": 104.0605, "desc": "大型科普场馆"},
    {"name": "东郊记忆", "lat": 30.6215, "lng": 104.0930, "desc": "原东区音乐公园"},
]

metro_stations = [
    {"name": "天府广场站", "lat": 30.6593, "lng": 104.0632, "lines": "1/2号线"},
    {"name": "春熙路站", "lat": 30.6582, "lng": 104.0644, "lines": "2/3号线"},
    {"name": "骡马市站", "lat": 30.6702, "lng": 104.0629, "lines": "1/4号线"},
    {"name": "宽窄巷子站", "lat": 30.6740, "lng": 104.0569, "lines": "4号线"},
    {"name": "人民公园站", "lat": 30.6630, "lng": 104.0620, "lines": "2号线"},
    {"name": "通惠门站", "lat": 30.6755, "lng": 104.0520, "lines": "2号线"},
    {"name": "中医大省医院站", "lat": 30.6818, "lng": 104.0505, "lines": "2/4号线"},
    {"name": "红星桥站", "lat": 30.6785, "lng": 104.0820, "lines": "3号线"},
    {"name": "市二医院站", "lat": 30.6655, "lng": 104.0765, "lines": "3/4号线"},
    {"name": "磨子桥站", "lat": 30.6435, "lng": 104.0680, "lines": "3号线"},
    {"name": "新南门站", "lat": 30.6500, "lng": 104.0735, "lines": "3号线"},
    {"name": "红牌楼站", "lat": 30.6305, "lng": 104.0525, "lines": "3号线"},
    {"name": "高升桥站", "lat": 30.6360, "lng": 104.0485, "lines": "3号线"},
    {"name": "衣冠庙站", "lat": 30.6450, "lng": 104.0525, "lines": "3号线"},
    {"name": "省体育馆站", "lat": 30.6380, "lng": 104.0800, "lines": "1/3号线"},
    {"name": "倪家桥站", "lat": 30.6340, "lng": 104.0805, "lines": "1/8号线"},
    {"name": "桐梓林站", "lat": 30.6250, "lng": 104.0820, "lines": "1/7号线"},
    {"name": "火车南站", "lat": 30.6180, "lng": 104.0835, "lines": "1/7号线"},
    {"name": "天府站", "lat": 30.6080, "lng": 104.0735, "lines": "1/18号线"},
    {"name": "孵化园站", "lat": 30.5950, "lng": 104.0685, "lines": "1/9号线"},
]

bus_stations = [
    {"name": "天府广场南站", "lat": 30.6575, "lng": 104.0635},
    {"name": "春熙路南站", "lat": 30.6565, "lng": 104.0648},
    {"name": "宽窄巷子站", "lat": 30.6735, "lng": 104.0575},
    {"name": "武侯祠站", "lat": 30.6520, "lng": 104.0550},
    {"name": "人民公园站", "lat": 30.6625, "lng": 104.0625},
    {"name": "总府路站", "lat": 30.6645, "lng": 104.0680},
    {"name": "红星路站", "lat": 30.6700, "lng": 104.0750},
    {"name": "玉双路站", "lat": 30.6780, "lng": 104.0850},
    {"name": "水碾河站", "lat": 30.6620, "lng": 104.0850},
    {"name": "九眼桥站", "lat": 30.6480, "lng": 104.0750},
    {"name": "科华北路站", "lat": 30.6380, "lng": 104.0750},
]

hotels = [
    {"name": "成都香格里拉大酒店", "lat": 30.6575, "lng": 104.0765, "stars": "5星"},
    {"name": "成都博舍酒店", "lat": 30.6545, "lng": 104.0695, "stars": "5星"},
    {"name": "成都富力丽思卡尔顿酒店", "lat": 30.6520, "lng": 104.0815, "stars": "5星"},
    {"name": "成都茂业JW万豪酒店", "lat": 30.6640, "lng": 104.0765, "stars": "4星"},
    {"name": "成都群光君悦酒店", "lat": 30.6588, "lng": 104.0642, "stars": "4星"},
    {"name": "成都瑞吉酒店", "lat": 30.6565, "lng": 104.0735, "stars": "5星"},
    {"name": "成都锦江宾馆", "lat": 30.6650, "lng": 104.0645, "stars": "4星"},
    {"name": "成都四川宾馆", "lat": 30.6700, "lng": 104.0580, "stars": "4星"},
    {"name": "成都京川宾馆", "lat": 30.6755, "lng": 104.0465, "stars": "4星"},
]

main_roads = [
    {"name": "人民南路", "coords": [[30.6593, 104.0632], [30.6300, 104.0800], [30.6000, 104.0750]]},
    {"name": "天府大道", "coords": [[30.6593, 104.0632], [30.6200, 104.0700], [30.5800, 104.0680]]},
    {"name": "红星路", "coords": [[30.6700, 104.0500], [30.6700, 104.0750], [30.6700, 104.0900]]},
    {"name": "总府路", "coords": [[30.6645, 104.0550], [30.6645, 104.0700], [30.6645, 104.0800]]},
    {"name": "春熙路", "coords": [[30.6582, 104.0580], [30.6582, 104.0700]]},
    {"name": "东大街", "coords": [[30.6650, 104.0500], [30.6650, 104.0750], [30.6500, 104.0800]]},
    {"name": "浆洗街", "coords": [[30.6500, 104.0500], [30.6400, 104.0500]]},
    {"name": "一环路", "coords": [
        [30.6900, 104.0400], [30.6900, 104.0500], [30.6900, 104.0600],
        [30.6900, 104.0700], [30.6900, 104.0800], [30.6900, 104.0900],
        [30.6800, 104.0950], [30.6700, 104.0950], [30.6600, 104.0950],
        [30.6500, 104.0950], [30.6400, 104.0950], [30.6300, 104.0950],
        [30.6200, 104.0900], [30.6100, 104.0850], [30.6000, 104.0800],
        [30.5900, 104.0750], [30.5900, 104.0650], [30.5900, 104.0550],
        [30.6000, 104.0450], [30.6100, 104.0400], [30.6200, 104.0350],
        [30.6300, 104.0300], [30.6400, 104.0300], [30.6500, 104.0300],
        [30.6600, 104.0300], [30.6700, 104.0300], [30.6800, 104.0350]
    ]},
    {"name": "二环路", "coords": [
        [30.7100, 104.0500], [30.7100, 104.0600], [30.7100, 104.0700],
        [30.7100, 104.0800], [30.7100, 104.0900], [30.7000, 104.1000],
        [30.6900, 104.1000], [30.6800, 104.1000], [30.6700, 104.1000],
        [30.6600, 104.1000], [30.6500, 104.1000], [30.6400, 104.1000],
        [30.6300, 104.0950], [30.6200, 104.0900], [30.6100, 104.0850],
        [30.6000, 104.0800], [30.5900, 104.0750], [30.5800, 104.0700],
        [30.5700, 104.0650], [30.5700, 104.0550], [30.5700, 104.0450],
        [30.5800, 104.0350], [30.5900, 104.0300], [30.6000, 104.0250],
        [30.6100, 104.0200], [30.6200, 104.0200], [30.6300, 104.0200],
        [30.6400, 104.0200], [30.6500, 104.0200], [30.6600, 104.0200],
        [30.6700, 104.0200], [30.6800, 104.0250], [30.6900, 104.0300],
        [30.7000, 104.0350]
    ]},
]

def add_markers(data, category, icon_name):
    group = folium.FeatureGroup(name=category)
    for item in data:
        color = icon_colors.get(category, "blue")
        if category == "酒店":
            popup = f"{item['name']}<br>{item['stars']}"
        elif category == "地铁站":
            popup = f"{item['name']}<br>线路: {item.get('lines', '')}"
        else:
            popup = item.get('desc', '') or item['name']
        
        folium.Marker(
            location=[item["lat"], item["lng"]],
            popup=popup,
            tooltip=item["name"],
            icon=folium.Icon(color=color, icon=icon_name)
        ).add_to(group)
    return group

def add_roads(roads):
    group = folium.FeatureGroup(name="主干道路")
    for road in roads:
        folium.PolyLine(
            locations=road["coords"],
            color="#FF6600",
            weight=4,
            opacity=0.8,
            popup=road["name"]
        ).add_to(group)
    return group

m.add_child(add_markers(spots, "景点", "info-sign"))
m.add_child(add_markers(metro_stations, "地铁站", "train"))
m.add_child(add_markers(bus_stations, "公交站", "bus"))
m.add_child(add_markers(hotels, "酒店", "home"))
m.add_child(add_roads(main_roads))

folium.Circle(
    location=[30.6580, 104.0658],
    radius=6000,
    color="#3388ff",
    fill=True,
    fillOpacity=0.1,
    popup="成都二环范围"
).add_to(m)

m.add_child(Fullscreen())
m.add_child(MousePosition())
folium.LayerControl(collapsed=False).add_to(m)

output_file = "/Users/Shared/_AllDocMap/02_Project/github/opencode/packages/opencode/chengdu_map.html"
m.save(output_file)
print(f"地图已生成: {output_file}")
print("包含: 14个景点, 20个地铁站, 11个公交站, 9个酒店, 9条主干道")