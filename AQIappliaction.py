import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QCheckBox, QFrame, QComboBox, QToolBar, QAction, QInputDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QUrl
import folium
import ee
import os
import folium.raster_layers
import geopandas as gpd
import geemap
from sqlalchemy import create_engine

class AQIApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.industries_gdf = gpd.GeoDataFrame()  # Initialize as an empty GeoDataFrame
        self.roads_gdf = gpd.GeoDataFrame()  # Initialize as an empty GeoDataFrame
        self.buffered_layers = []
        print("Initializing application...")
        # Initialize Earth Engine
        ee.Authenticate()
        ee.Initialize(project='ee-javaidzainab2018')
        self.setWindowTitle("AQI Mapping Application")
        self.setGeometry(100, 100, 1000, 600)
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        # Toolbar
        self.create_tool_bar()
        # Define a dictionary for seasonal date ranges
        self.season_dates = {
            "Spring": ("2024-03-01", "2024-05-31"),
            "Summer": ("2024-06-01", "2024-09-30"),
            "Autumn": ("2024-10-01", "2024-11-30"),
            "Winter": ("2023-12-01", "2024-02-29")
        }
        # Side Panel
        self.left_panel = self.create_side_panel()
        self.main_layout.addWidget(self.left_panel)
        # Map Viewer
        self.map_viewer = self.create_map_viewer()
        self.main_layout.addWidget(self.map_viewer)
        print("Application initialized successfully.")

    def create_tool_bar(self):
        print("Creating toolbar...")
        tool_bar = QToolBar("Pollutants Toolbar", self)
        self.addToolBar(tool_bar)
        
        # Pollutant 1 (NO2) with season selection
        self.no2_selector = QComboBox()
        self.no2_selector.addItem("Spring")
        self.no2_selector.addItem("Summer")
        self.no2_selector.addItem("Autumn")
        self.no2_selector.addItem("Winter")
        self.no2_selector.currentTextChanged.connect(
            lambda: self.update_pollutant_data(
                'NO2',
                self.no2_selector.currentText(),
                *self.season_dates[self.no2_selector.currentText()]
            )
        )
        no2_action = QAction(QIcon(), 'NO2', self)
        tool_bar.addAction(no2_action)
        tool_bar.addWidget(self.no2_selector)
        tool_bar.addSeparator()
        
        # Pollutant 2 (SO2) with season selection
        self.so2_selector = QComboBox()
        self.so2_selector.addItem("Spring")
        self.so2_selector.addItem("Summer")
        self.so2_selector.addItem("Autumn")
        self.so2_selector.addItem("Winter")
        self.so2_selector.currentTextChanged.connect(
            lambda: self.update_pollutant_data(
                'SO2',
                self.so2_selector.currentText(),
                *self.season_dates[self.so2_selector.currentText()]
            )
        )
        so2_action = QAction(QIcon(), 'SO2', self)
        tool_bar.addAction(so2_action)
        tool_bar.addWidget(self.so2_selector)
        tool_bar.addSeparator()
        
        # Pollutant 3 (O3) with season selection
        self.o3_selector = QComboBox()
        self.o3_selector.addItem("Spring")
        self.o3_selector.addItem("Summer")
        self.o3_selector.addItem("Autumn")
        self.o3_selector.addItem("Winter")
        self.o3_selector.currentTextChanged.connect(
            lambda: self.update_pollutant_data(
                'O3',
                self.o3_selector.currentText(),
                *self.season_dates[self.o3_selector.currentText()]
            )
        )
        o3_action = QAction(QIcon(), 'O3', self)
        tool_bar.addAction(o3_action)
        tool_bar.addWidget(self.o3_selector)
        tool_bar.addSeparator()
        
        # Pollutant 4 (PM2.5) with season selection
        self.pm_selector = QComboBox()
        self.pm_selector.addItem("Spring")
        self.pm_selector.addItem("Summer")
        self.pm_selector.addItem("Autumn")
        self.pm_selector.addItem("Winter")
        self.pm_selector.currentTextChanged.connect(
            lambda: self.update_pollutant_data(
                'PM2.5',
                self.pm_selector.currentText(),
                *self.season_dates[self.pm_selector.currentText()]
            )
        )
        
        pm_action = QAction(QIcon(), 'PM2.5', self)
        tool_bar.addAction(pm_action)
        tool_bar.addWidget(self.pm_selector)
        tool_bar.addSeparator()

        # Add "Exit" button
        exit_action = QAction(QIcon(), "Exit", self)
        exit_action.triggered.connect(self.close_application)
        tool_bar.addAction(exit_action)

        print("Toolbar created successfully.")

    def create_side_panel(self):
        print("Creating side panel...")
        panel = QFrame()
        panel.setStyleSheet("background-color: #d9f2d9;")
        panel.setFixedWidth(220)
        layout = QVBoxLayout(panel)

        # Title at the top of the side panel
        title_label = QLabel("AQI Mapping Application")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2d6a4f; margin-bottom: 20px;")
        layout.addWidget(title_label)

        # Location Info
        location_label = QLabel("📍 Lahore")
        location_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(location_label)

        # Layers Section
        layers_label = QLabel("Layers")
        layers_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(layers_label)

        # Layer checkboxes
        self.roads_checkbox = QCheckBox("Roads")
        self.roads_checkbox.setStyleSheet("font-size: 14px;")
        self.roads_checkbox.stateChanged.connect(self.update_map)
        layout.addWidget(self.roads_checkbox)

        # Industries checkbox with buffer input dialog
        self.industries_checkbox = QCheckBox("Industries with Buffer")
        self.industries_checkbox.setStyleSheet("font-size: 14px;")
        self.industries_checkbox.stateChanged.connect(self.on_industries_checkbox_state_changed)
        layout.addWidget(self.industries_checkbox)
        # Legend container
        self.legend_layout = QVBoxLayout()
        self.legend_layout.setContentsMargins(5, 5, 5, 5)
        self.legend_layout.setSpacing(3)
        legend_container = QWidget()
        legend_container.setLayout(self.legend_layout)
        layout.addWidget(legend_container)
        layout.addStretch()
        print("Side panel created successfully.")

        layout.addStretch()
        print("Side panel created successfully.")
        return panel

    def create_map_viewer(self):
        print("Creating map viewer...")
        # Create the folium map
        self.map = folium.Map(location=[31.5497, 74.3436], zoom_start=10)  # Lahore coordinates
        # Add Lahore shapefile boundary
        self.add_lahore_shapefile()
        # Add base marker for Lahore
        folium.Marker([31.5497, 74.3436], tooltip="Lahore").add_to(self.map)
        # Load shapefiles for roads and industries
        self.load_shapefiles()
        # Save the map to an HTML file in the current working directory
        self.map_file = os.path.join(os.getcwd(), "map.html")
        self.map.save(self.map_file)
        print(f"Map saved to: {self.map_file}")  # Debugging file path
        # Embed the map in QWebEngineView
        self.web_view = QWebEngineView()
        self.web_view.load(QUrl.fromLocalFile(self.map_file)) 
        print("Map viewer created successfully.")
        return self.web_view

    def add_lahore_shapefile(self):
        print("Adding Lahore shapefile...")
        shapefile_path = r'D:\Python Project\python files\Lahore Boundary' 
        gdf = gpd.read_file(shapefile_path)
        geojson_data = gdf.to_json()
        folium.GeoJson(
            geojson_data,
            name="Lahore Boundary",
            style_function=lambda x: {'fillColor': 'none', 'color': 'red', 'weight': 2, 'fillOpacity': 0.5}
        ).add_to(self.map)
        print("Lahore shapefile added.")

    def load_shapefiles(self):
        print("Loading shapefiles for roads and industries from PostgreSQL database...")
        try:
            print("Attempting to connect to the database...")
            # connect and add database details
            db_password = os.environ.get('DB_PASSWORD')
            engine = create_engine(f'postgresql+psycopg://postgres:{db_password}@localhost:5432/AQIApplication')
            print("Database Connection Successful")
            
            # Load the roads shapefile from the database
            self.roads_gdf = gpd.read_postgis("SELECT * FROM lahore_road_network", engine, geom_col='geom')
            self.roads_gdf.set_crs(epsg=4326, inplace=True)  # Set CRS for roads GeoDataFrame
            print("Road shapefile loaded successfully!")
            print(self.roads_gdf.head())
            
            # Load the industries shapefile from the database
            self.industries_gdf = gpd.read_postgis("SELECT * FROM lahore_industry_points", engine, geom_col='geom')
            self.industries_gdf.set_crs(epsg=4326, inplace=True)  # Set CRS for industries GeoDataFrame
            print("Industries shapefile loaded successfully!")
            print(self.industries_gdf.head())
            
        except Exception as e:
            print(f"Error loading shapefiles: {e}")
        
        return self.industries_gdf

    def update_pollutant_data(self, pollutant, season, start_date, end_date):
        print(f"Updating {pollutant} data for {season}: {start_date} to {end_date}")
        shapefile_path = r'D:\Python Project\python files\Lahore Boundary' 
        gdf = gpd.read_file(shapefile_path)
        roi = geemap.gdf_to_ee(gdf)
        vis_params = {
            'NO2': {'min': 0, 'max': 0.0002, 'palette': ['green', 'yellow', 'orange', 'red', 'purple'],
                    'thresholds': [0, 0.00004, 0.00008, 0.00012, 0.00016, 0.0002]},
            'SO2': {'min': 0, 'max': 0.0005, 'palette': ['green', 'yellow', 'orange', 'red', 'purple'],
                    'thresholds': [0, 0.0001, 0.0002, 0.0003, 0.0004, 0.0005]},
            'O3': {'min': 0, 'max': 0.15, 'palette': ['green', 'yellow', 'orange', 'red', 'purple'],
                   'thresholds': [0, 0.02, 0.05, 0.08, 0.12, 0.15]},
            'PM2.5': {'min': 0, 'max': 1, 'palette': ['green', 'yellow', 'orange', 'red', 'purple'],
                      'thresholds': [0, 0.2, 0.4, 0.6, 0.8, 1]}
        }
        datasets = {
            'NO2': {'id': 'COPERNICUS/S5P/OFFL/L3_NO2', 'band': 'tropospheric_NO2_column_number_density'},
            'SO2': {'id': 'COPERNICUS/S5P/OFFL/L3_SO2', 'band': 'SO2_column_number_density'},
            'O3': {'id': 'COPERNICUS/S5P/OFFL/L3_O3', 'band': 'O3_column_number_density'},
            'PM2.5': {'id': 'COPERNICUS/S5P/OFFL/L3_AER_AI', 'band': 'absorbing_aerosol_index'}
        }
        pollutant_info = datasets[pollutant]
        dataset = ee.ImageCollection(pollutant_info['id']) \
            .filterDate(start_date, end_date) \
            .filterBounds(roi) \
            .select(pollutant_info['band']) \
            .mean()
        clip_pollutant_image = dataset.clip(roi)
        map_center = [31.5497, 74.3436]
        self.map = folium.Map(location=map_center, zoom_start=10)
        map_id_dict = clip_pollutant_image.getMapId(vis_params[pollutant])
        folium.raster_layers.TileLayer(
            tiles=map_id_dict['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            name=f"{pollutant} ({start_date}, {end_date})",
            overlay=True,
            control=True,
            show=True
        ).add_to(self.map)
        self.add_layers_to_map(self.map)
        folium.LayerControl().add_to(self.map)
        self.update_legend(self.map, pollutant, season, vis_params, start_date, end_date)
        map_file = f'{pollutant}_map.html'
        self.map.save(map_file)
        self.map_file = map_file
        map_url = QUrl(f'file:///{map_file}')
        self.map_viewer.setUrl(map_url)
        print(f"{pollutant} data updated for {season}.")

    def update_legend(self, m, pollutant, season, vis_params, start_date, end_date):
        print(f"Updating legend for {pollutant} from {start_date} to {end_date}.")
        pollutant_params = vis_params[pollutant]
        palette = pollutant_params['palette']
        thresholds = vis_params[pollutant]['thresholds']
        for i in reversed(range(self.legend_layout.count())):
            widget = self.legend_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        title_label = QLabel(f"AQI Map of {pollutant}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.legend_layout.addWidget(title_label)
        date_label = QLabel(f"{season}\n{start_date} to {end_date}")
        date_label.setStyleSheet("font-size: 12px; color: #555;")
        self.legend_layout.addWidget(date_label)
        for i, color in enumerate(palette):
            if i < len(thresholds) - 1:
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(5)
                color_box = QLabel()
                color_box.setFixedSize(20, 20)
                color_box.setStyleSheet(f"background-color: {color}; border: 1px solid black;")
                range_label = QLabel(f"{thresholds[i]} - {thresholds[i + 1]}")
                range_label.setStyleSheet("font-size: 12px; margin-left: 5px; color: #333;")
                row_layout.addWidget(color_box)
                row_layout.addWidget(range_label)
                row_layout.addStretch()
                self.legend_layout.addWidget(row_widget)
        print(f"Legend updated for {pollutant} from {start_date} to {end_date}.")

    def update_map(self):
        print("Updating map based on layer selections...")
        self.map = folium.Map(location=[31.5497, 74.3436], zoom_start=10)
        self.add_lahore_shapefile()
        self.add_layers_to_map(self.map)
        self.map.save(self.map_file)
        self.map_file = self.map_file
        self.web_view.load(QUrl.fromLocalFile(self.map_file))
        print("Map updated.")

    def add_layers_to_map(self, m):
        print("Adding layers to the map...")
        if self.industries_checkbox.isChecked():
            print("Adding industries layer...")
            for _, row in self.industries_gdf.iterrows():
                lon, lat = row.geom.x, row.geom.y
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=1.2,
                    color="black",
                    fill=True,
                    fill_color="black",
                    fill_opacity=0.8
                ).add_to(m)
        if self.roads_checkbox.isChecked():
            print("Adding roads layer...")
            for _, row in self.roads_gdf.iterrows():
                geom = row.geom
                if geom.geom_type == 'LineString':
                    coords = [(point[1], point[0]) for point in geom.coords]
                    folium.PolyLine(
                        locations=coords,
                        color="blue",
                        weight=2,
                        opacity=0.8
                    ).add_to(m)
                elif geom.geom_type == 'MultiLineString':
                    for line in geom.geoms:
                        coords = [(point[1], point[0]) for point in line.coords]
                        folium.PolyLine(
                            locations=coords,
                            color="blue",
                            weight=2,
                            opacity=0.8
                        ).add_to(m)
        print("Layers added to the map.")

    def close_application(self):
        print("Closing application...")
        self.close()

    def on_industries_checkbox_state_changed(self, state):
        if state == Qt.Checked:
            buffer_value, ok = QInputDialog.getDouble(self, "Buffer Input", "Enter buffer value (meters):", min=0.0)
            if ok:
                print(f"Buffer value entered: {buffer_value} meters")
                self.add_buffer_to_industries(buffer_value)
        else:
            self.clear_buffer_layers()

    def clear_buffer_layers(self):
        print("Clearing previous buffer layers...")
        for layer in self.buffered_layers:
            layer.remove_from(self.map)
        self.buffered_layers = []  # clear the buffer list
        self.map.save(self.map_file)
        self.web_view.load(QUrl.fromLocalFile(self.map_file))
        print("Previous buffer layers cleared.")

    def add_buffer_to_industries(self, buffer_value):
        print(f"Adding buffer of {buffer_value} meters to industries...")
        # Clear previous layers
        self.clear_buffer_layers()

        # Re-project to a projected CRS for accurate buffering
        projected_gdf = self.industries_gdf.to_crs(epsg=3857)
        buffered_gdf = projected_gdf.copy()
        buffered_gdf['geometry'] = buffered_gdf.geometry.buffer(buffer_value)

        # Re-project back to the original CRS
        buffered_gdf = buffered_gdf.to_crs(epsg=4326)

        for _, row in buffered_gdf.iterrows():
            if row['geometry'] is not None:
                print(f"Adding buffer for geometry: {row['geometry']}")
                buffer_layer = folium.GeoJson(row['geometry'].__geo_interface__)
                buffer_layer.add_to(self.map)
                self.buffered_layers.append(buffer_layer)

        self.map.save(self.map_file)
        self.map_file = self.map_file
        self.web_view.load(QUrl.fromLocalFile(self.map_file))
        print("Buffer added to industries.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AQIApp()
    window.show()
    sys.exit(app.exec_())
