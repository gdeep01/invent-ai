import React from 'react'
import gsap from 'gsap'
import * as THREE from 'three'

const vertexShader = `
  varying vec2 vUv;

  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`

const fragmentShader = `
  precision highp float;

  varying vec2 vUv;

  uniform float uTime;
  uniform vec2 uResolution;
  uniform vec2 uMouse;
  uniform float uIntro;

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
  }

  float noise(in vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);

    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));

    vec2 u = f * f * (3.0 - 2.0 * f);

    return mix(a, b, u.x) +
      (c - a) * u.y * (1.0 - u.x) +
      (d - b) * u.x * u.y;
  }

  float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;

    for (int i = 0; i < 6; i++) {
      value += amplitude * noise(p);
      p *= 2.02;
      amplitude *= 0.5;
    }

    return value;
  }

  mat2 rotate2d(float angle) {
    float s = sin(angle);
    float c = cos(angle);
    return mat2(c, -s, s, c);
  }

  void main() {
    vec2 uv = vUv;
    vec2 centered = uv - 0.5;
    centered.x *= uResolution.x / uResolution.y;

    vec2 mouse = uMouse - 0.5;
    mouse.x *= uResolution.x / uResolution.y;

    float distToMouse = length(centered - mouse);
    float mouseField = exp(-distToMouse * 5.5);

    vec2 flowUv = centered;
    flowUv *= rotate2d(uTime * 0.08 + mouse.x * 0.8);
    flowUv += mouse * 0.2;

    float n1 = fbm(flowUv * 1.2 + vec2(0.0, uTime * 0.08));
    float n2 = fbm(flowUv * 2.0 - vec2(uTime * 0.05, 0.0));
    float n3 = fbm((flowUv + n1) * 3.4 + mouseField);

    float bands = smoothstep(0.1, 0.95, n1 * 0.55 + n2 * 0.3 + n3 * 0.4);
    float mist = smoothstep(0.2, 1.0, n2 + mouseField * 0.35);
    float shimmer = smoothstep(0.55, 1.0, sin((n3 + uTime * 0.12) * 6.2831) * 0.5 + 0.5);

    vec3 baseColor = vec3(0.01, 0.04, 0.08);
    vec3 color1 = vec3(0.0, 0.7, 0.6);
    vec3 color2 = vec3(0.0, 0.5, 0.8);
    vec3 color3 = vec3(0.0, 0.3, 0.5);
    vec3 color4 = vec3(0.1, 0.8, 0.7);
    vec3 color5 = vec3(0.0, 0.6, 0.9);

    vec3 color = baseColor;
    color = mix(color, color1, bands * 0.55);
    color = mix(color, color2, mist * 0.45);
    color = mix(color, color3, smoothstep(0.2, 0.85, n3) * 0.35);
    color = mix(color, color4, mouseField * 0.5);
    color = mix(color, color5, shimmer * 0.2);

    float vignette = smoothstep(1.25, 0.15, length(centered));
    color *= vignette;

    float introMask = smoothstep(0.0, 1.0, uIntro);
    color *= introMask;
    color *= 0.9;

    gl_FragColor = vec4(color, 1.0);
  }
`

export const TurbulentFlow = ({ children }) => {
  const containerRef = React.useRef(null)

  React.useEffect(() => {
    const container = containerRef.current
    if (!container) return undefined

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setClearColor(0x020617, 1)
    container.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)

    const uniforms = {
      uTime: { value: 0 },
      uResolution: { value: new THREE.Vector2(container.clientWidth, container.clientHeight) },
      uMouse: { value: new THREE.Vector2(0.5, 0.5) },
      uIntro: { value: 0 },
    }

    const material = new THREE.ShaderMaterial({
      uniforms,
      vertexShader,
      fragmentShader,
    })

    const geometry = new THREE.PlaneGeometry(2, 2)
    const mesh = new THREE.Mesh(geometry, material)
    scene.add(mesh)

    const targetMouse = new THREE.Vector2(0.5, 0.5)
    const currentMouse = new THREE.Vector2(0.5, 0.5)

    const timeline = gsap.timeline()
    timeline.to(uniforms.uIntro, {
      value: 1,
      duration: 1.4,
      ease: 'power2.out',
    })

    const handlePointerMove = (event) => {
      const bounds = container.getBoundingClientRect()
      targetMouse.x = (event.clientX - bounds.left) / bounds.width
      targetMouse.y = 1 - (event.clientY - bounds.top) / bounds.height
    }

    const handleResize = () => {
      if (!container) return
      const width = container.clientWidth
      const height = container.clientHeight
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.setSize(width, height)
      uniforms.uResolution.value.set(width, height)
    }

    container.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('resize', handleResize)

    const clock = new THREE.Clock()
    let frameId = 0

    const render = () => {
      frameId = window.requestAnimationFrame(render)
      currentMouse.lerp(targetMouse, 0.06)
      uniforms.uMouse.value.copy(currentMouse)
      uniforms.uTime.value = clock.getElapsedTime()
      renderer.render(scene, camera)
    }

    render()

    return () => {
      window.cancelAnimationFrame(frameId)
      timeline.kill()
      container.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('resize', handleResize)
      scene.remove(mesh)
      geometry.dispose()
      material.dispose()
      renderer.dispose()
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  return (
    <div className="relative h-full min-h-screen w-full overflow-hidden">
      <div ref={containerRef} className="absolute inset-0" aria-hidden="true" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(15,23,42,0.18),rgba(2,6,23,0.55)_55%,rgba(2,6,23,0.88)_100%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(2,6,23,0.08),rgba(2,6,23,0.38)_65%,rgba(2,6,23,0.72)_100%)]" />
      <div className="relative h-full min-h-screen">{children}</div>
    </div>
  )
}
