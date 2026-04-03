import folium
from folium.plugins import Fullscreen, MousePosition, MiniMap

shanghai_map = folium.Map(
    location=[31.2300, 121.4600],
    zoom_start=12,
    tiles=None
)

folium.TileLayer(
    tiles="https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
    attr='高德地图',
    name="高德地图"
).add_to(shanghai_map)

folium.TileLayer(
    tiles="https://map.geoq.cn/ArcGIS/rest/services/ChinaOnlineCommunity/MapServer/tile/{z}/{y}/{x}",
    attr='GeoQ',
    name="在线地图"
).add_to(shanghai_map)

style_html = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
.title-box {
    background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
    border: none;
    border-radius: 12px;
    padding: 18px 24px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    color: white;
    font-family: 'Noto Sans SC', sans-serif;
}
.title-box h3 {
    margin: 0 0 6px 0;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1px;
}
.title-box p {
    margin: 0;
    font-size: 12px;
    opacity: 0.9;
    font-weight: 300;
}
.legend-box {
    background: rgba(255,255,255,0.95);
    border-radius: 10px;
    padding: 14px 18px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    font-family: 'Noto Sans SC', sans-serif;
    border: 1px solid #e0e0e0;
}
.legend-box h5 {
    margin: 0 0 10px 0;
    color: #2c3e50;
    font-size: 13px;
    font-weight: 600;
    border-bottom: 2px solid #3498db;
    padding-bottom: 6px;
}
.legend-item {
    display: flex;
    align-items: center;
    margin: 6px 0;
    font-size: 11px;
    color: #555;
}
.leaflet-control-layers {
    font-family: 'Noto Sans SC', sans-serif;
}
.popup-custom {
    font-family: 'Noto Sans SC', sans-serif;
    padding: 5px;
    min-width: 180px;
}
.popup-custom h4 {
    margin: 0 0 6px 0;
    color: #1a5276;
    font-size: 15px;
    font-weight: 600;
}
.popup-custom .cat {
    display: inline-block;
    background: #3498db;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    margin-bottom: 6px;
}
.popup-custom .desc {
    color: #666;
    font-size: 11px;
    line-height: 1.5;
}
</style>
'''
shanghai_map.get_root().html.add_child(folium.Element(style_html))

title_html = '''
<div class="title-box" style="position: fixed; top: 15px; left: 60px; z-index: 9999;">
    <h3>上海市静安区</h3>
    <p>景点 · 地铁 · 公交 · 酒店 · 商圈</p>
</div>
'''
shanghai_map.get_root().html.add_child(folium.Element(title_html))

legend_html = '''
<div class="legend-box" style="position: fixed; bottom: 30px; left: 20px; z-index: 9999; width: 160px;">
    <h5>图例</h5>
    <div class="legend-item"><i style="width:12px;height:12px;background:#e74c3c;display:inline-block;border-radius:50%;"></i> 景点</div>
    <div class="legend-item"><i style="width:12px;height:12px;background:#3498db;display:inline-block;border-radius:50%;"></i> 地铁站</div>
    <div class="legend-item"><i style="width:12px;height:12px;background:#27ae60;display:inline-block;border-radius:50%;"></i> 公交站</div>
    <div class="legend-item"><i style="width:12px;height:12px;background:#f39c12;display:inline-block;border-radius:50%;"></i> 酒店</div>
    <div class="legend-item"><i style="width:12px;height:12px;background:#9b59b6;display:inline-block;border-radius:50%;"></i> 商圈</div>
</div>
'''
shanghai_map.get_root().html.add_child(folium.Element(legend_html))

jingan_boundary = [
    [31.2690, 121.4440],
    [31.2670, 121.4480],
    [31.2640, 121.4520],
    [31.2600, 121.4550],
    [31.2550, 121.4580],
    [31.2500, 121.4600],
    [31.2450, 121.4630],
    [31.2400, 121.4660],
    [31.2350, 121.4680],
    [31.2300, 121.4700],
    [31.2280, 121.4720],
    [31.2260, 121.4740],
    [31.2240, 121.4760],
    [31.2220, 121.4780],
    [31.2200, 121.4800],
    [31.2180, 121.4800],
    [31.2160, 121.4790],
    [31.2140, 121.4770],
    [31.2120, 121.4750],
    [31.2100, 121.4730],
    [31.2080, 121.4700],
    [31.2060, 121.4670],
    [31.2040, 121.4640],
    [31.2020, 121.4600],
    [31.2000, 121.4560],
    [31.1980, 121.4520],
    [31.1960, 121.4480],
    [31.1940, 121.4440],
    [31.1920, 121.4400],
    [31.1900, 121.4360],
    [31.1880, 121.4320],
    [31.1900, 121.4280],
    [31.1920, 121.4240],
    [31.1940, 121.4200],
    [31.1960, 121.4160],
    [31.1980, 121.4120],
    [31.2000, 121.4080],
    [31.2020, 121.4040],
    [31.2040, 121.4000],
    [31.2060, 121.3960],
    [31.2080, 121.3920],
    [31.2100, 121.3880],
    [31.2120, 121.3840],
    [31.2140, 121.3800],
    [31.2200, 121.3800],
    [31.2260, 121.3800],
    [31.2320, 121.3800],
    [31.2380, 121.3800],
    [31.2440, 121.3800],
    [31.2500, 121.3800],
    [31.2560, 121.3800],
    [31.2620, 121.3800],
    [31.2680, 121.3800],
    [31.2700, 121.3850],
    [31.2710, 121.3900],
    [31.2710, 121.4000],
    [31.2710, 121.4100],
    [31.2710, 121.4200],
    [31.2700, 121.4300],
    [31.2690, 121.4400],
]

spots = [
    {"name": "静安寺", "lat": 31.2285, "lng": 121.4729, "desc": "上海最古老的佛寺之一，千年古刹"},
    {"name": "静安公园", "lat": 31.2295, "lng": 121.4715, "desc": "静安寺旁的开放式公园"},
    {"name": "上海展览中心", "lat": 31.2210, "lng": 121.4650, "desc": "俄罗斯风格建筑，重要展览场馆"},
    {"name": "中共二大会址纪念馆", "lat": 31.2355, "lng": 121.4755, "desc": "中国共产党第二次全国代表大会会址"},
    {"name": "毛泽东旧居", "lat": 31.2270, "lng": 121.4685, "desc": "毛泽东在上海的寓所旧址"},
    {"name": "蔡元培故居", "lat": 31.2335, "lng": 121.4720, "desc": "著名教育家蔡元培故居"},
    {"name": "自然博物馆", "lat": 31.2195, "lng": 121.4535, "desc": "综合性自然科学博物馆"},
    {"name": "闸北公园", "lat": 31.2445, "lng": 121.4620, "desc": "原名宋教仁公园，上海老牌公园"},
]

metro_stations = [
    {"name": "静安寺站", "lat": 31.2285, "lng": 121.4729, "lines": "2/7/14号线"},
    {"name": "江苏路站", "lat": 31.2225, "lng": 121.4535, "lines": "2/11号线"},
    {"name": "中山公园站", "lat": 31.2185, "lng": 121.4335, "lines": "2/3/4号线"},
    {"name": "娄山关路站", "lat": 31.2115, "lng": 121.4155, "lines": "2/15号线"},
    {"name": "威宁路站", "lat": 31.2175, "lng": 121.4065, "lines": "2号线"},
    {"name": "北新泾站", "lat": 31.2245, "lng": 121.3965, "lines": "2号线"},
    {"name": "淞虹路站", "lat": 31.2175, "lng": 121.3865, "lines": "2号线"},
    {"name": "人民广场站", "lat": 31.2275, "lng": 121.4780, "lines": "1/2/8号线"},
    {"name": "南京西路站", "lat": 31.2280, "lng": 121.4650, "lines": "2/12/13号线"},
    {"name": "汉中路站", "lat": 31.2395, "lng": 121.4615, "lines": "1/12/13号线"},
    {"name": "上海火车站站", "lat": 31.2515, "lng": 121.4515, "lines": "1/3/4号线"},
    {"name": "彭浦新村站", "lat": 31.2620, "lng": 121.4460, "lines": "1号线"},
]

bus_stations = [
    {"name": "静安寺站", "lat": 31.2280, "lng": 121.4735},
    {"name": "南京西路站", "lat": 31.2280, "lng": 121.4655},
    {"name": "镇宁路站", "lat": 31.2250, "lng": 121.4575},
    {"name": "江苏路站", "lat": 31.2220, "lng": 121.4545},
    {"name": "中山公园站", "lat": 31.2190, "lng": 121.4350},
    {"name": "长宁路站", "lat": 31.2220, "lng": 121.4250},
    {"name": "天山路站", "lat": 31.2100, "lng": 121.4200},
    {"name": "玉屏南路站", "lat": 31.2130, "lng": 121.4080},
    {"name": "北渔路站", "lat": 31.2180, "lng": 121.3950},
    {"name": "共和新路站", "lat": 31.2480, "lng": 121.4650},
    {"name": "闸北公园站", "lat": 31.2440, "lng": 121.4625},
]

hotels = [
    {"name": "上海静安香格里拉大酒店", "lat": 31.2265, "lng": 121.4685, "stars": "★★★★★"},
    {"name": "上海波特曼丽思卡尔顿酒店", "lat": 31.2205, "lng": 121.4685, "stars": "★★★★★"},
    {"name": "上海静安瑞吉酒店", "lat": 31.2305, "lng": 121.4715, "stars": "★★★★★"},
    {"name": "上海四季酒店", "lat": 31.2250, "lng": 121.4645, "stars": "★★★★★"},
    {"name": "上海璞丽酒店", "lat": 31.2215, "lng": 121.4715, "stars": "★★★★★"},
    {"name": "上海镛舍酒店", "lat": 31.2230, "lng": 121.4680, "stars": "★★★★★"},
    {"name": "上海明天广场JW万豪酒店", "lat": 31.2275, "lng": 121.4785, "stars": "★★★★"},
    {"name": "上海国际贵都大饭店", "lat": 31.2225, "lng": 121.4585, "stars": "★★★★"},
    {"name": "上海宾馆", "lat": 31.2295, "lng": 121.4555, "stars": "★★★★"},
    {"name": "上海锦江之星", "lat": 31.2410, "lng": 121.4625, "stars": "★★★"},
]

business_areas = [
    {"name": "静安寺商圈", "lat": 31.2285, "lng": 121.4729, "desc": "高端商业区，奢侈品聚集地"},
    {"name": "南京西路商圈", "lat": 31.2275, "lng": 121.4650, "desc": "上海最繁华的商业街之一"},
    {"name": "中山公园商圈", "lat": 31.2185, "lng": 121.4335, "desc": "长宁区核心商业中心"},
    {"name": "大宁商圈", "lat": 31.2595, "lng": 121.4595, "desc": "闸北区新兴商圈"},
    {"name": "苏河湾商圈", "lat": 31.2445, "lng": 121.4775, "desc": "苏州河畔商业文化区"},
]

def add_boundary():
    group = folium.FeatureGroup(name="行政区界")
    folium.Polygon(
        locations=jingan_boundary,
        color="#2c3e50",
        weight=3,
        fill=True,
        fillColor="#3498db",
        fillOpacity=0.15,
        popup="静安区行政边界"
    ).add_to(group)
    return group

def add_spots():
    group = folium.FeatureGroup(name="景点")
    for item in spots:
        folium.Marker(
            location=[item["lat"], item["lng"]],
            popup=f"""
            <div class="popup-custom">
                <h4>{item['name']}</h4>
                <span class="cat">景点</span>
                <p class="desc">{item['desc']}</p>
            </div>
            """,
            tooltip=f"{item['name']}",
            icon=folium.Icon(color="red", icon="star")
        ).add_to(group)
    return group

def add_metro():
    group = folium.FeatureGroup(name="地铁站")
    for item in metro_stations:
        folium.Marker(
            location=[item["lat"], item["lng"]],
            popup=f"""
            <div class="popup-custom">
                <h4>{item['name']}</h4>
                <span class="cat">地铁站</span>
                <p class="desc">线路: {item['lines']}</p>
            </div>
            """,
            tooltip=f"{item['name']} - {item['lines']}",
            icon=folium.Icon(color="blue", icon="train")
        ).add_to(group)
    return group

def add_bus():
    group = folium.FeatureGroup(name="公交站")
    for item in bus_stations:
        folium.Marker(
            location=[item["lat"], item["lng"]],
            popup=f"<b>{item['name']}</b>",
            tooltip=item["name"],
            icon=folium.Icon(color="green", icon="bus")
        ).add_to(group)
    return group

def add_hotels():
    group = folium.FeatureGroup(name="酒店")
    for item in hotels:
        folium.Marker(
            location=[item["lat"], item["lng"]],
            popup=f"""
            <div class="popup-custom">
                <h4>{item['name']}</h4>
                <span class="cat" style="background:#f39c12;">{item['stars']}</span>
            </div>
            """,
            tooltip=f"{item['name']} {item['stars']}",
            icon=folium.Icon(color="orange", icon="home")
        ).add_to(group)
    return group

def add_business():
    group = folium.FeatureGroup(name="商圈")
    for item in business_areas:
        folium.Circle(
            location=[item["lat"], item["lng"]],
            radius=250,
            color="#9b59b6",
            fill=True,
            fillOpacity=0.25,
            popup=f"""
            <div class="popup-custom">
                <h4>{item['name']}</h4>
                <p class="desc">{item['desc']}</p>
            </div>
            """
        ).add_to(group)
        folium.Marker(
            location=[item["lat"], item["lng"]],
            popup=f"""
            <div class="popup-custom">
                <h4>{item['name']}</h4>
                <span class="cat" style="background:#9b59b6;">商圈</span>
                <p class="desc">{item['desc']}</p>
            </div>
            """,
            tooltip=item["name"],
            icon=folium.Icon(color="purple", icon="shopping-cart")
        ).add_to(group)
    return group

shanghai_map.add_child(add_boundary())
shanghai_map.add_child(add_spots())
shanghai_map.add_child(add_metro())
shanghai_map.add_child(add_bus())
shanghai_map.add_child(add_hotels())
shanghai_map.add_child(add_business())

shanghai_map.add_child(Fullscreen())
shanghai_map.add_child(MousePosition())
MiniMap(toggle_preset=True, position="bottomleft").add_to(shanghai_map)
folium.LayerControl(collapsed=False, position="topright").add_to(shanghai_map)

output_file = "/Users/Shared/_AllDocMap/02_Project/github/opencode/packages/opencode/shanghai_jingan_map.html"
shanghai_map.save(output_file)
print(f"地图已生成: {output_file}")
print("包含: 行政区界, 8个景点, 12个地铁站, 11个公交站, 10个酒店, 5个商圈")