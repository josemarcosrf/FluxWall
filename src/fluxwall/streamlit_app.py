"""Streamlit UI for FluxWall."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlencode

import requests
import streamlit as st

# Configure page
st.set_page_config(
    page_title='FluxWall — Parametric Live Wallpaper Creator',
    page_icon='🎨',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ─── Constants ────────────────────────────────────────────────────

API_BASE = 'http://localhost:8000/api'
GENERATORS_ENDPOINT = f'{API_BASE}/generators'
PRESETS_ENDPOINT = f'{API_BASE}/presets'
PREVIEW_ENDPOINT = f'{API_BASE}/preview/stream'
EXPORT_ENDPOINT = f'{API_BASE}/export'

IPHONE_MODELS = {
    'iPhone 15/16 Pro Max': (1290, 2796),
    'iPhone 15/16 Pro': (1179, 2556),
    'iPhone 14/13/12 Pro': (1170, 2532),
    'iPhone SE': (750, 1334),
}

EXPORT_FORMATS = {
    'MP4 (Video)': 'mp4',
    'MOV (iOS Video)': 'mov',
    'Live Photo (HEIC+MOV)': 'live_photo',
}

# Generators whose generate_frame is still a scaffold/placeholder (see STATUS.md).
# Kept selectable so users can see what's coming, but greyed out and blocked from export.
UNIMPLEMENTED_GENERATORS = {'l_system', 'color_cycle'}


# ─── Helper Functions ─────────────────────────────────────────────


@st.cache_data(ttl=60)
def fetch_generators() -> list[dict[str, Any]]:
    """Fetch available generators from API."""
    try:
        resp = requests.get(GENERATORS_ENDPOINT, timeout=5)
        resp.raise_for_status()
        result = resp.json()
        assert isinstance(result, list)
        return result
    except Exception as e:
        st.error(f'Failed to fetch generators: {e}')
        return []


@st.cache_data(ttl=60)
def fetch_presets(generator: str | None = None) -> list[dict[str, Any]]:
    """Fetch presets from API."""
    try:
        params = {'generator': generator} if generator else {}
        resp = requests.get(PRESETS_ENDPOINT, params=params, timeout=5)
        resp.raise_for_status()
        result = resp.json()
        assert isinstance(result, list)
        return result
    except Exception as e:
        st.error(f'Failed to fetch presets: {e}')
        return []


def create_param_widgets(param_schema: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create Streamlit widgets for generator parameters."""
    if defaults is None:
        defaults = {}

    params: dict[str, Any] = {}
    properties = param_schema.get('properties', {})

    for name, schema in properties.items():
        if name in ('width', 'height', 'fps', 'duration_sec', 'colormap', 'seed'):
            continue  # Skip base params handled separately

        param_type = schema.get('type')
        default = defaults.get(name, schema.get('default'))

        try:
            if param_type == 'boolean':
                params[name] = st.checkbox(
                    name.replace('_', ' ').title(),
                    value=bool(default),
                    key=f'param_{name}',
                )
            elif param_type == 'integer':
                params[name] = st.number_input(
                    name.replace('_', ' ').title(),
                    value=int(default) if default is not None else 0,
                    min_value=schema.get('minimum'),
                    max_value=schema.get('maximum'),
                    step=1,
                    key=f'param_{name}',
                )
            elif param_type == 'number':
                params[name] = st.number_input(
                    name.replace('_', ' ').title(),
                    value=float(default) if default is not None else 0.0,
                    min_value=schema.get('minimum'),
                    max_value=schema.get('maximum'),
                    step=schema.get('exclusiveMinimum', 0.1),
                    format='%.4f',
                    key=f'param_{name}',
                )
            elif param_type == 'string':
                enum = schema.get('enum')
                if enum:
                    params[name] = st.selectbox(
                        name.replace('_', ' ').title(),
                        options=enum,
                        index=enum.index(default) if default in enum else 0,
                        key=f'param_{name}',
                    )
                elif schema.get('format') == 'color':
                    params[name] = st.color_picker(
                        name.replace('_', ' ').title(),
                        value=default or '#ffffff',
                        key=f'param_{name}',
                    )
                else:
                    params[name] = st.text_input(
                        name.replace('_', ' ').title(),
                        value=str(default) if default is not None else '',
                        key=f'param_{name}',
                    )
            elif param_type == 'object':
                # For complex objects, use JSON input
                json_str = st.text_area(
                    name.replace('_', ' ').title(),
                    value=json.dumps(default, indent=2) if default else '{}',
                    key=f'param_{name}',
                )
                try:
                    params[name] = json.loads(json_str)
                except json.JSONDecodeError:
                    st.error(f'Invalid JSON for {name}')
                    params[name] = default or {}
        except Exception as e:
            st.error(f'Error creating widget for {name}: {e}')
            params[name] = default

    return params


def get_preset_params(presets: list[dict[str, Any]], preset_name: str | None) -> dict[str, Any]:
    """Get parameters from a selected preset."""
    if not preset_name:
        return {}
    for p in presets:
        if p['name'] == preset_name:
            result = p.get('params')
            if isinstance(result, dict):
                return result
    return {}


# ─── Main App ────────────────────────────────────────────────────


def main() -> None:
    # Custom CSS
    st.markdown(
        """
        <style>
        .stImage > img {
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .preview-container {
            aspect-ratio: 9/19.5;
            overflow: hidden;
        }
        .metric-card {
            background: #f0f2f6;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Header
    st.title('🎨 FluxWall')
    st.caption('Parametric iOS Live Wallpaper Generator')

    # Check API connectivity
    if 'api_connected' not in st.session_state:
        try:
            resp = requests.get('http://localhost:8000/health', timeout=2)
            st.session_state.api_connected = resp.status_code == 200
        except Exception:
            st.session_state.api_connected = False

    if not st.session_state.api_connected:
        st.error('⚠️ Cannot connect to API server. Start it with `just api` or `just dev`')
        st.stop()

    # ─── Sidebar: Generator Selection ─────────────────────────────

    with st.sidebar:
        st.header('🎯 Generator')

        generators = fetch_generators()
        if not generators:
            st.error('No generators available')
            st.stop()

        def label_for(g: dict[str, Any]) -> str:
            display_name = str(g.get('display_name') or g.get('name') or '')
            if g['name'] in UNIMPLEMENTED_GENERATORS:
                return f'🚧 {display_name} (not implemented)'
            return display_name

        gen_names = [label_for(g) for g in generators]
        gen_map = {label_for(g): g['name'] for g in generators}

        selected_gen_name = st.selectbox(
            'Select Generator',
            gen_names,
            key='selected_generator',
        )

        generator = gen_map[selected_gen_name]
        gen_info = next(g for g in generators if g['name'] == generator)
        is_unimplemented = generator in UNIMPLEMENTED_GENERATORS

        st.markdown(f'*{gen_info["description"]}*')
        if is_unimplemented:
            st.warning('🚧 This generator is scaffolded only — it does not render its real algorithm yet.')
            st.caption('Preview/export are disabled.')

        # ─── Preset Selection ─────────────────────────────────────

        st.divider()
        st.header('💾 Presets')

        presets = fetch_presets(generator)
        preset_names = ['— Custom —'] + [p['name'] for p in presets]

        selected_preset = st.selectbox(
            'Load Preset',
            preset_names,
            key='selected_preset',
        )

        if selected_preset != '— Custom —':
            preset_params = get_preset_params(presets, selected_preset)
            if st.button('Apply Preset', width='stretch'):
                st.session_state.applied_preset = preset_params
                st.rerun()

        # ─── Base Parameters ──────────────────────────────────────

        st.divider()
        st.header('📐 Target Resolution')

        iphone_model = st.selectbox(
            'iPhone Model',
            list(IPHONE_MODELS.keys()),
            index=2,
        )

        ipw, iph = IPHONE_MODELS[iphone_model]
        st.markdown(f'**{ipw}×{iph}**  ')
        st.caption('Preview runs at low res for performance; export uses full resolution.')
        preview_scale = 0.25  # Preview at 25% of full resolution

        col1, col2 = st.columns(2)
        with col1:
            fps = st.slider('FPS', 1, 60, 30)
        with col2:
            duration = st.slider('Duration (s)', 0.5, 30.0, 3.0, 0.5)

        colormap = st.selectbox(
            'Colormap',
            ['magma', 'viridis', 'plasma', 'inferno', 'cividis', 'twilight', 'turbo', 'hot', 'fire', 'plasma_r'],
            index=0,
        )

        seed_val = st.number_input('Seed (optional)', value=0, min_value=0, max_value=2**31 - 1)
        seed: int | None = seed_val if seed_val != 0 else None

        # ─── Generator-Specific Parameters ────────────────────────

        st.divider()
        st.header('⚙️ Generator Parameters')

        # Get preset params if applied
        preset_defaults = st.session_state.get('applied_preset', {})
        if preset_defaults:
            st.info('Using preset parameters')

        gen_params = create_param_widgets(gen_info['param_schema'], preset_defaults)

        with st.expander('ℹ️ Parameter Info', expanded=False):
            schema = gen_info['param_schema']
            props = schema.get('properties', {})
            for name, prop in props.items():
                if name in ('width', 'height', 'fps', 'duration_sec', 'colormap', 'seed'):
                    continue
                ptype = prop.get('type', '').title()
                info_parts = [f'**{name}** ({ptype})']
                if 'default' in prop:
                    info_parts.append(f'default: `{prop["default"]}`')
                if 'minimum' in prop:
                    info_parts.append(f'min: {prop["minimum"]}')
                if 'maximum' in prop:
                    info_parts.append(f'max: {prop["maximum"]}')
                if 'enum' in prop:
                    info_parts.append(f'options: `{"`, `".join(str(e) for e in prop["enum"])}`')
                st.markdown('  • ' + '  • '.join(info_parts))

        # ─── Export Options ───────────────────────────────────────

        st.divider()
        st.header('📤 Export')

        export_format = st.selectbox(
            'Format',
            list(EXPORT_FORMATS.keys()),
            index=0,
        )

        export_fps = st.slider('Export FPS', 1, 60, 30)
        export_duration = st.slider('Export Duration (s)', 0.5, 30.0, 3.0, 0.5)
        quality = st.slider('Quality', 10, 100, 90)

        # ─── Export Button ────────────────────────────────────────

        if is_unimplemented:
            st.button('🚀 Generate & Export', type='primary', width='stretch', disabled=True)
            st.caption('Export disabled — this generator is not implemented yet.')
        elif st.button('🚀 Generate & Export', type='primary', width='stretch'):
            export_wallpaper(
                generator,
                gen_params,
                export_format,
                iphone_model,
                export_fps,
                export_duration,
                quality,
            )

    # ─── Main Preview Area ────────────────────────────────────────

    # Preview at reduced resolution for performance
    prev_w = int(ipw * preview_scale)
    prev_h = int(iph * preview_scale)

    preview_params = {
        'width': prev_w,
        'height': prev_h,
        'fps': 15,
        'duration_sec': 60,
        'colormap': colormap,
        'seed': seed,
        **gen_params,
    }

    # Create preview URL — pass params as JSON string
    query = urlencode(
        {
            'generator': generator,
            'params': json.dumps(preview_params),
            'fps': 15,
        }
    )
    preview_url = f'{PREVIEW_ENDPOINT}?{query}'

    # Preview — phone-sized display at low res
    st.subheader('📺 Live Preview')
    st.caption(f'Generating at {prev_w}×{prev_h} for speed  •  Export at full {ipw}×{iph}')

    display_width = min(prev_w, 400)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button('▶️ Play', width='stretch'):
            st.session_state.preview_playing = True
    with col2:
        if st.button('⏸️ Pause', width='stretch'):
            st.session_state.preview_playing = False
    with col3:
        if st.button('🔄 Reset', width='stretch'):
            st.session_state.preview_key = time.time()

    # Centered phone preview
    lcol, mcol, rcol = st.columns([1, 2, 1])
    with mcol:
        preview_placeholder = st.empty()

        if is_unimplemented:
            preview_placeholder.info('🚧 No real preview available — this generator is scaffolded only.')
        elif st.session_state.get('preview_playing', True):
            preview_placeholder.image(
                preview_url,
                caption=f'{selected_gen_name}  •  {prev_w}×{prev_h}  •  15 FPS',
                width=display_width,
            )
        else:
            try:
                resp = requests.get(preview_url, timeout=5, stream=True)
                for chunk in resp.iter_content(chunk_size=1024):
                    if chunk:
                        preview_placeholder.image(chunk, caption='Paused', width=display_width)
                        break
            except Exception:
                preview_placeholder.info('Preview paused. Click Play to resume.')

    # Status metrics
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Frames', f'{int(fps * duration)}')
    with col2:
        st.metric('Export Res', f'{ipw}×{iph}')
    with col3:
        st.metric('Preview', f'{prev_w}×{prev_h}')
    with col4:
        est_size = (ipw * iph * 3 * fps * duration) / (1024 * 1024)
        st.metric('Est. Size', f'{est_size:.1f} MB (raw)')


def export_wallpaper(
    generator: str,
    gen_params: dict[str, Any],
    export_format: str,
    iphone_model: str,
    export_fps: int,
    export_duration: float,
    quality: int,
) -> None:
    """Trigger export via API."""
    iphone_w, iphone_h = IPHONE_MODELS[iphone_model]
    format_key = EXPORT_FORMATS[export_format]

    # Build request
    payload = {
        'generator': generator,
        'params': {
            **gen_params,
            'width': iphone_w,
            'height': iphone_h,
            'fps': export_fps,
            'duration_sec': export_duration,
        },
        'options': {
            'format': format_key,
            'iphone_model': iphone_model.lower().replace(' ', '_').replace('/', '_'),
            'fps': export_fps,
            'duration_sec': export_duration,
            'quality': quality,
        },
    }

    # Show progress
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text('🚀 Starting export...')
        progress_bar.progress(10)

        resp = requests.post(f'{EXPORT_ENDPOINT}', json=payload, timeout=300)  # type: ignore[arg-type]
        resp.raise_for_status()
        result = resp.json()

        job_id = result.get('job_id')
        download_url = result.get('download_url')

        status_text.text('⏳ Generating frames...')
        progress_bar.progress(50)

        # Poll for completion
        status_url = f'{API_BASE}/export/status/{job_id}'
        for _ in range(60):  # Max 60 seconds
            try:
                status_resp = requests.get(status_url, timeout=5)
                status_data = status_resp.json()

                if status_data.get('status') == 'completed':
                    progress_bar.progress(100)
                    status_text.text('✅ Export complete!')

                    # Provide download
                    if download_url:
                        file_resp = requests.get(f'http://localhost:8000{download_url}', stream=True, timeout=60)
                        if file_resp.status_code == 200:
                            filename = download_url.split('/')[-1]
                            st.download_button(
                                f'📥 Download {export_format}',
                                data=file_resp.content,
                                file_name=filename,
                                mime='application/octet-stream',
                                width='stretch',
                            )
                    break
                if status_data.get('status') == 'failed':
                    st.error(f'Export failed: {status_data.get("error", "Unknown error")}')
                    break

                progress = status_data.get('progress', 0)
                progress_bar.progress(50 + int(progress * 50))
                time.sleep(1)

            except Exception as e:
                st.warning(f'Status check failed: {e}')
                break

    except requests.exceptions.RequestException as e:
        st.error(f'Export failed: {e}')
    except Exception as e:
        st.error(f'Unexpected error: {e}')


if __name__ == '__main__':
    main()
