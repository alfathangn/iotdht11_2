# app_streamlit_final.py - WORKING VERSION
import streamlit as st
import time
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import threading
import json

# Page configuration - MUST BE FIRST
st.set_page_config(
    page_title="Dashboard Monitoring Suhu DHT22",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Header styling */
    .main-header {
        font-size: 2.5rem;
        color: #4361ee;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 700;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        margin-bottom: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Status indicators */
    .status-connected {
        background-color: #4cc9f0;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
        box-shadow: 0 0 10px #4cc9f0;
        animation: pulse 2s infinite;
    }
    
    .status-disconnected {
        background-color: #f72585;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
        box-shadow: 0 0 10px #f72585;
    }
    
    /* LED indicators */
    .led-container {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin: 10px 0;
    }
    
    .led-indicator {
        width: 25px;
        height: 25px;
        border-radius: 50%;
        box-shadow: 0 0 10px rgba(0,0,0,0.3);
    }
    
    .led-red { background-color: #f72585; }
    .led-green { background-color: #4cc9f0; }
    .led-yellow { background-color: #f8961e; }
    .led-off { background-color: #666666; }
    
    /* Animation */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = {
        'temperature': 24.0,
        'humidity': 65.0,
        'status': 'Normal',
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'led_states': {'merah': False, 'hijau': True, 'kuning': False},
        'led_status': 'LED Hijau Menyala',
        'mqtt_connected': False,
        'last_update': datetime.now()
    }

if 'history' not in st.session_state:
    st.session_state.history = []

if 'mqtt_initialized' not in st.session_state:
    st.session_state.mqtt_initialized = False

# SIMULATOR - Generate realistic sensor data
def sensor_simulator():
    """Simulate DHT22 sensor data"""
    while True:
        time.sleep(2)  # Update every 2 seconds
        
        # Simulate realistic temperature fluctuations
        base_temp = 24.0
        temp_variation = random.uniform(-2, 3)
        temperature = base_temp + temp_variation
        
        # Simulate humidity
        base_humidity = 65.0
        hum_variation = random.uniform(-5, 5)
        humidity = base_humidity + hum_variation
        
        # Determine status
        if temperature < 22:
            status = 'Dingin'
            led_states = {'merah': False, 'hijau': False, 'kuning': True}
            led_status = 'LED Kuning Menyala'
        elif temperature > 25:
            status = 'Panas'
            led_states = {'merah': True, 'hijau': False, 'kuning': False}
            led_status = 'LED Merah Menyala'
        else:
            status = 'Normal'
            led_states = {'merah': False, 'hijau': True, 'kuning': False}
            led_status = 'LED Hijau Menyala'
        
        # Update session state
        st.session_state.sensor_data.update({
            'temperature': temperature,
            'humidity': humidity,
            'status': status,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'led_states': led_states,
            'led_status': led_status,
            'last_update': datetime.now()
        })
        
        # Add to history (keep last 50 readings)
        st.session_state.history.append({
            'time': datetime.now(),
            'temperature': temperature,
            'humidity': humidity,
            'status': status
        })
        
        if len(st.session_state.history) > 50:
            st.session_state.history.pop(0)
        
        # Trigger rerun if in auto-refresh mode
        if st.session_state.get('auto_refresh', True):
            st.rerun()

# Start simulator thread
if 'sim_thread' not in st.session_state:
    sim_thread = threading.Thread(target=sensor_simulator, daemon=True)
    sim_thread.start()
    st.session_state.sim_thread = sim_thread

# Sidebar
with st.sidebar:
    st.title("⚙️ Kontrol Dashboard")
    
    # Connection status
    st.markdown("### 🔗 Status Koneksi")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.session_state.sensor_data['mqtt_connected']:
            st.markdown('<div class="status-connected"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-disconnected"></div>', unsafe_allow_html=True)
    with col2:
        if st.session_state.sensor_data['mqtt_connected']:
            st.success("Terhubung MQTT")
        else:
            st.warning("Mode Simulasi")
    
    # Auto-refresh toggle
    st.markdown("### 🔄 Auto Refresh")
    auto_refresh = st.toggle("Aktifkan Auto-refresh", value=True, key="auto_refresh_toggle")
    st.session_state.auto_refresh = auto_refresh
    
    # Manual data control
    st.markdown("### 🎮 Kontrol Manual")
    
    col1, col2 = st.columns(2)
    with col1:
        manual_temp = st.number_input(
            "Suhu (°C)",
            min_value=15.0,
            max_value=35.0,
            value=st.session_state.sensor_data['temperature'],
            step=0.1,
            key="temp_input"
        )
    with col2:
        manual_hum = st.number_input(
            "Kelembaban (%)",
            min_value=30.0,
            max_value=90.0,
            value=st.session_state.sensor_data['humidity'],
            step=0.1,
            key="hum_input"
        )
    
    if st.button("💾 Simpan Data Manual", type="secondary", use_container_width=True):
        # Determine status based on manual input
        if manual_temp < 22:
            status = 'Dingin'
            led_states = {'merah': False, 'hijau': False, 'kuning': True}
            led_status = 'LED Kuning Menyala'
        elif manual_temp > 25:
            status = 'Panas'
            led_states = {'merah': True, 'hijau': False, 'kuning': False}
            led_status = 'LED Merah Menyala'
        else:
            status = 'Normal'
            led_states = {'merah': False, 'hijau': True, 'kuning': False}
            led_status = 'LED Hijau Menyala'
        
        st.session_state.sensor_data.update({
            'temperature': manual_temp,
            'humidity': manual_hum,
            'status': status,
            'led_states': led_states,
            'led_status': led_status,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'last_update': datetime.now()
        })
        st.success("✅ Data berhasil disimpan!")
        time.sleep(1)
        st.rerun()
    
    # LED Controls
    st.markdown("### 💡 Kontrol LED")
    
    # Individual LED controls
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔴", help="LED Merah", use_container_width=True):
            st.session_state.sensor_data['led_states'] = {'merah': True, 'hijau': False, 'kuning': False}
            st.session_state.sensor_data['led_status'] = 'LED Merah Menyala'
            st.rerun()
    with col2:
        if st.button("🟢", help="LED Hijau", use_container_width=True):
            st.session_state.sensor_data['led_states'] = {'merah': False, 'hijau': True, 'kuning': False}
            st.session_state.sensor_data['led_status'] = 'LED Hijau Menyala'
            st.rerun()
    with col3:
        if st.button("🟡", help="LED Kuning", use_container_width=True):
            st.session_state.sensor_data['led_states'] = {'merah': False, 'hijau': False, 'kuning': True}
            st.session_state.sensor_data['led_status'] = 'LED Kuning Menyala'
            st.rerun()
    
    # All controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 ALL ON", type="primary", use_container_width=True):
            st.session_state.sensor_data['led_states'] = {'merah': True, 'hijau': True, 'kuning': True}
            st.session_state.sensor_data['led_status'] = 'Semua LED Menyala'
            st.rerun()
    with col2:
        if st.button("🚫 ALL OFF", type="secondary", use_container_width=True):
            st.session_state.sensor_data['led_states'] = {'merah': False, 'hijau': False, 'kuning': False}
            st.session_state.sensor_data['led_status'] = 'Semua LED Mati'
            st.rerun()
    
    # Clear history
    if st.button("🗑️ Hapus Riwayat", type="secondary", use_container_width=True):
        st.session_state.history.clear()
        st.success("Riwayat berhasil dihapus!")
        time.sleep(1)
        st.rerun()
    
    # System info
    st.markdown("---")
    st.markdown("### 🖥️ Sistem Info")
    st.caption("**Sensor:** DHT22")
    st.caption("**Range Normal:** 22°C - 25°C")
    st.caption("**Update Interval:** 2 detik")
    st.caption(f"**Data Points:** {len(st.session_state.history)}")

# Main dashboard
st.markdown('<h1 class="main-header">🌡️ Dashboard Monitoring Suhu DHT22</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666; margin-bottom: 2rem;">Update Real-time • Sistem IoT • ESP32 + DHT22</p>', unsafe_allow_html=True)

# Row 1: Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    
    # Temperature with color indicator
    temp = st.session_state.sensor_data['temperature']
    status = st.session_state.sensor_data['status']
    
    # Color based on status
    if status == 'Dingin':
        color = "#4cc9f0"  # Blue
        icon = "❄️"
    elif status == 'Panas':
        color = "#f72585"  # Red
        icon = "🔥"
    else:
        color = "#4ade80"  # Green
        icon = "✅"
    
    st.markdown(f'<h2 style="color: {color}; margin: 0;">{icon} {temp:.1f}°C</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="margin: 5px 0; font-size: 1.2rem;">Suhu</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="color: rgba(255,255,255,0.8); margin: 0;">Status: <strong>{status}</strong></p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    
    # Humidity with progress bar
    humidity = st.session_state.sensor_data['humidity']
    
    st.markdown(f'<h2 style="color: #4cc9f0; margin: 0;">💧 {humidity:.1f}%</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="margin: 5px 0; font-size: 1.2rem;">Kelembaban</p>', unsafe_allow_html=True)
    
    # Progress bar
    progress = min(humidity / 100, 1.0)
    st.progress(progress, text=f"{int(humidity)}%")
    
    # Humidity level indicator
    if humidity < 40:
        level = "Rendah"
    elif humidity < 70:
        level = "Normal"
    else:
        level = "Tinggi"
    
    st.markdown(f'<p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0;">Level: <strong>{level}</strong></p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    
    # Last update time
    last_update = st.session_state.sensor_data['last_update']
    elapsed = (datetime.now() - last_update).seconds
    
    st.markdown(f'<h2 style="color: #f8961e; margin: 0;">🕒 {st.session_state.sensor_data["timestamp"]}</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="margin: 5px 0; font-size: 1.2rem;">Update Terakhir</p>', unsafe_allow_html=True)
    
    # Time since last update
    if elapsed < 5:
        time_text = "Baru saja"
        time_color = "#4ade80"
    elif elapsed < 30:
        time_text = f"{elapsed} detik lalu"
        time_color = "#f8961e"
    else:
        time_text = f"{elapsed} detik lalu"
        time_color = "#f72585"
    
    st.markdown(f'<p style="color: {time_color}; margin: 5px 0;">{time_text}</p>', unsafe_allow_html=True)
    
    # Auto-refresh indicator
    if st.session_state.get('auto_refresh', True):
        st.markdown('<p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0;">Auto-refresh: <strong>Aktif</strong></p>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0;">Auto-refresh: <strong>Nonaktif</strong></p>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    
    # LED Status
    st.markdown(f'<h2 style="color: #ffffff; margin: 0;">💡 LED Status</h2>', unsafe_allow_html=True)
    
    # LED indicators
    led_states = st.session_state.sensor_data['led_states']
    led_html = '<div class="led-container">'
    
    colors = ['red', 'green', 'yellow']
    for color in colors:
        if led_states.get(color, False):
            led_html += f'<div class="led-indicator led-{color}" title="LED {color.capitalize()} ON"></div>'
        else:
            led_html += f'<div class="led-indicator led-off" title="LED {color.capitalize()} OFF"></div>'
    
    led_html += '</div>'
    st.markdown(led_html, unsafe_allow_html=True)
    
    # LED status text
    led_status = st.session_state.sensor_data['led_status']
    st.markdown(f'<p style="text-align: center; color: rgba(255,255,255,0.9); margin: 10px 0 0 0;"><strong>{led_status}</strong></p>', unsafe_allow_html=True)
    
    # LED count
    active_leds = sum(led_states.values())
    st.markdown(f'<p style="text-align: center; color: rgba(255,255,255,0.7); margin: 5px 0 0 0;">Aktif: {active_leds}/3</p>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Row 2: Charts
st.markdown("## 📈 Grafik Monitoring Real-time")

if st.session_state.history:
    # Create tabs for different charts
    tab1, tab2, tab3 = st.tabs(["📊 Grafik Suhu", "💧 Grafik Kelembaban", "📋 Data Riwayat"])
    
    with tab1:
        # Prepare data for temperature chart
        times = [h['time'] for h in st.session_state.history]
        temps = [h['temperature'] for h in st.session_state.history]
        statuses = [h['status'] for h in st.session_state.history]
        
        # Create temperature chart
        fig_temp = go.Figure()
        
        # Add temperature line
        fig_temp.add_trace(go.Scatter(
            x=times,
            y=temps,
            mode='lines+markers',
            name='Suhu',
            line=dict(color='#4361ee', width=3),
            marker=dict(size=6, color='#4361ee'),
            hovertemplate='<b>%{x:%H:%M:%S}</b><br>Suhu: %{y:.1f}°C<extra></extra>'
        ))
        
        # Add threshold lines
        fig_temp.add_hline(
            y=22,
            line_dash="dash",
            line_color="blue",
            annotation_text="Batas Dingin (22°C)",
            annotation_position="bottom right"
        )
        
        fig_temp.add_hline(
            y=25,
            line_dash="dash", 
            line_color="red",
            annotation_text="Batas Panas (25°C)",
            annotation_position="top right"
        )
        
        # Color background based on status
        for i in range(len(times)-1):
            color = {
                'Dingin': 'rgba(76, 201, 240, 0.1)',
                'Normal': 'rgba(74, 222, 128, 0.1)',
                'Panas': 'rgba(247, 37, 133, 0.1)'
            }.get(statuses[i], 'rgba(0,0,0,0.1)')
            
            fig_temp.add_shape(
                type="rect",
                x0=times[i],
                x1=times[i+1],
                y0=min(temps)-2,
                y1=max(temps)+2,
                fillcolor=color,
                opacity=0.3,
                layer="below",
                line_width=0
            )
        
        fig_temp.update_layout(
            title='Riwayat Suhu (°C) - Real-time',
            xaxis_title='Waktu',
            yaxis_title='Suhu (°C)',
            template='plotly_white',
            height=400,
            hovermode='x unified',
            showlegend=True
        )
        
        st.plotly_chart(fig_temp, use_container_width=True)
        
        # Temperature statistics
        if temps:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Rata-rata", f"{sum(temps)/len(temps):.1f}°C")
            with col2:
                st.metric("Tertinggi", f"{max(temps):.1f}°C")
            with col3:
                st.metric("Terendah", f"{min(temps):.1f}°C")
            with col4:
                current_status = st.session_state.sensor_data['status']
                st.metric("Status", current_status)
    
    with tab2:
        # Humidity chart
        hums = [h['humidity'] for h in st.session_state.history]
        
        fig_hum = go.Figure()
        fig_hum.add_trace(go.Scatter(
            x=times,
            y=hums,
            mode='lines+markers',
            name='Kelembaban',
            line=dict(color='#4cc9f0', width=3),
            marker=dict(size=6, color='#4cc9f0'),
            hovertemplate='<b>%{x:%H:%M:%S}</b><br>Kelembaban: %{y:.1f}%<extra></extra>'
        ))
        
        # Add humidity comfort zones
        fig_hum.add_hrect(
            y0=40, y1=70,
            fillcolor="rgba(76, 201, 240, 0.1)",
            line_width=0,
            annotation_text="Zona Nyaman (40-70%)",
            annotation_position="top left"
        )
        
        fig_hum.update_layout(
            title='Riwayat Kelembaban (%) - Real-time',
            xaxis_title='Waktu',
            yaxis_title='Kelembaban (%)',
            template='plotly_white',
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_hum, use_container_width=True)
        
        # Humidity statistics
        if hums:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rata-rata", f"{sum(hums)/len(hums):.1f}%")
            with col2:
                st.metric("Tertinggi", f"{max(hums):.1f}%")
            with col3:
                st.metric("Terendah", f"{min(hums):.1f}%")
    
    with tab3:
        # Data table
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            df['Waktu'] = df['time'].dt.strftime('%H:%M:%S')
            df['Suhu (°C)'] = df['temperature'].round(1)
            df['Kelembaban (%)'] = df['humidity'].round(1)
            df['Status'] = df['status']
            
            # Show latest first
            df_display = df[['Waktu', 'Suhu (°C)', 'Kelembaban (%)', 'Status']].iloc[::-1]
            
            st.dataframe(
                df_display,
                use_container_width=True,
                height=400,
                column_config={
                    "Waktu": st.column_config.TextColumn("Waktu", width="small"),
                    "Suhu (°C)": st.column_config.NumberColumn("Suhu (°C)", format="%.1f"),
                    "Kelembaban (%)": st.column_config.NumberColumn("Kelembaban (%)", format="%.1f"),
                    "Status": st.column_config.TextColumn("Status")
                }
            )
            
            # Export options
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Download CSV", use_container_width=True):
                    csv = df_display.to_csv(index=False)
                    st.download_button(
                        label="Klik untuk download",
                        data=csv,
                        file_name=f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            with col2:
                if st.button("🔄 Refresh Data", use_container_width=True):
                    st.rerun()
else:
    # No data yet
    st.info("⏳ Menunggu data sensor... Data akan muncul dalam beberapa detik.")
    
    # Show loading animation
    with st.spinner("Menginisialisasi sensor..."):
        time.sleep(2)
        st.rerun()

# Row 3: System Information
st.markdown("## 🖥️ Informasi Sistem")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔧 Spesifikasi Sistem")
    
    sys_info = {
        "🌐 Jenis Dashboard": "Streamlit Real-time",
        "📡 Sensor": "DHT22 (Temperature & Humidity)",
        "⚡ Mikrokontroller": "ESP32",
        "☁️ Protokol Komunikasi": "MQTT (Simulasi)",
        "📊 Update Interval": "2 detik",
        "💾 Data History": f"{len(st.session_state.history)} titik data"
    }
    
    for key, value in sys_info.items():
        st.markdown(f"**{key}:** {value}")

with col2:
    st.markdown("### 🎯 Rentang Suhu")
    
    # Temperature range visualization
    current_temp = st.session_state.sensor_data['temperature']
    
    fig_range = go.Figure()
    
    # Add range areas
    fig_range.add_hrect(
        y0=15, y1=22,
        fillcolor="rgba(76, 201, 240, 0.3)",
        line_width=0,
        annotation_text="Dingin (<22°C)",
        annotation_position="inside top left"
    )
    
    fig_range.add_hrect(
        y0=22, y1=25,
        fillcolor="rgba(74, 222, 128, 0.3)",
        line_width=0,
        annotation_text="Normal (22-25°C)",
        annotation_position="inside top"
    )
    
    fig_range.add_hrect(
        y0=25, y1=35,
        fillcolor="rgba(247, 37, 133, 0.3)",
        line_width=0,
        annotation_text="Panas (>25°C)",
        annotation_position="inside top right"
    )
    
    # Add current temperature marker
    fig_range.add_trace(go.Scatter(
        x=[0.5],
        y=[current_temp],
        mode='markers+text',
        marker=dict(size=20, color='#000000'),
        text=[f"{current_temp:.1f}°C"],
        textposition="top center",
        name="Suhu Saat Ini"
    ))
    
    fig_range.update_layout(
        title="Visualisasi Rentang Suhu",
        yaxis_title="Suhu (°C)",
        xaxis=dict(showticklabels=False),
        height=250,
        showlegend=False,
        template="plotly_white"
    )
    
    st.plotly_chart(fig_range, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p style="font-size: 1.1rem; margin-bottom: 5px;">
        <strong>Sistem Monitoring Suhu DHT22</strong> • Real-time Dashboard
    </p>
    <p style="margin-bottom: 5px;">
        Dibimbing IoT Project • ESP32 + DHT22 • Streamlit
    </p>
    <p style="color: #4361ee; font-weight: 600;">
        Fariz • Update Terakhir: {} • Data Points: {}
    </p>
</div>
""".format(
    st.session_state.sensor_data['timestamp'],
    len(st.session_state.history)
), unsafe_allow_html=True)

# Auto-refresh logic
if st.session_state.get('auto_refresh', True):
    # Auto refresh every 2 seconds
    time.sleep(2)
    st.rerun()