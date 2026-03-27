/* Three.js 3D Viewport for RebarHelper */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

class RebarViewer3D {
  constructor(containerEl) {
    this.container = containerEl;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1a1a2e);

    // Camera
    this.camera = new THREE.PerspectiveCamera(50, 1, 0.1, 10000);
    this.camera.position.set(150, 100, 200);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    containerEl.appendChild(this.renderer.domElement);

    // Controls
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.1;

    // Raycaster
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    // Groups
    this.surfaceGroup = new THREE.Group();
    this.rebarGroup = new THREE.Group();
    this.scene.add(this.surfaceGroup);
    this.scene.add(this.rebarGroup);

    // Lights
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambient);
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(100, 200, 150);
    this.scene.add(dir);

    // Grid
    const grid = new THREE.GridHelper(500, 50, 0x444466, 0x333355);
    this.scene.add(grid);

    // Axes
    const axes = new THREE.AxesHelper(50);
    this.scene.add(axes);

    // Selection state
    this.selectedGroupId = null;
    this.onGroupSelected = null;

    // Store last bounds for zoom extents
    this._lastBounds = null;

    // Events
    this.renderer.domElement.addEventListener('click', (e) => this._onClick(e));
    window.addEventListener('resize', () => this._resize());
    this._resize();
    this._animate();
  }

  _resize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    if (w === 0 || h === 0) return;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  _animate() {
    requestAnimationFrame(() => this._animate());
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  _onClick(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.rebarGroup.children, true);

    // Reset previous selection
    this.rebarGroup.children.forEach(child => {
      if (child.userData.originalColor !== undefined) {
        child.material.color.setHex(child.userData.originalColor);
        child.material.emissive.setHex(0x000000);
      }
    });

    if (intersects.length > 0) {
      const hit = intersects[0].object;
      const groupId = hit.userData.groupId;
      this.selectedGroupId = groupId;

      this.rebarGroup.children.forEach(child => {
        if (child.userData.groupId === groupId) {
          child.material.emissive.setHex(0x444444);
        }
      });

      if (this.onGroupSelected) this.onGroupSelected(groupId);
    } else {
      this.selectedGroupId = null;
    }
  }

  clearScene() {
    while (this.surfaceGroup.children.length > 0) {
      const c = this.surfaceGroup.children[0];
      if (c.geometry) c.geometry.dispose();
      if (c.material) c.material.dispose();
      this.surfaceGroup.remove(c);
    }
    while (this.rebarGroup.children.length > 0) {
      const c = this.rebarGroup.children[0];
      if (c.geometry) c.geometry.dispose();
      if (c.material) c.material.dispose();
      this.rebarGroup.remove(c);
    }
  }

  update(data) {
    this.clearScene();
    if (!data) return;

    data.surfaces.forEach(s => {
      if (s.vertices.length < 3) return;
      this._renderSurface(s);
    });

    data.rebar_groups.forEach(g => {
      this._renderRebarGroup(g);
    });

    this._fitCamera(data.bounds);
  }

  _renderSurface(s) {
    const verts = s.vertices;
    const positions = [];
    for (let i = 1; i < verts.length - 1; i++) {
      positions.push(...verts[0], ...verts[i], ...verts[i + 1]);
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geo.computeVertexNormals();

    const mesh = new THREE.Mesh(geo, new THREE.MeshPhongMaterial({
      color: 0x8899aa,
      transparent: true,
      opacity: 0.12,
      side: THREE.DoubleSide,
      depthWrite: false,
    }));
    mesh.userData.surfaceId = s.id;
    this.surfaceGroup.add(mesh);

    // Wireframe edges
    const edgeGeo = new THREE.BufferGeometry();
    const edgeVerts = [];
    for (let i = 0; i < verts.length; i++) {
      const a = verts[i];
      const b = verts[(i + 1) % verts.length];
      edgeVerts.push(...a, ...b);
    }
    edgeGeo.setAttribute('position', new THREE.Float32BufferAttribute(edgeVerts, 3));
    const line = new THREE.LineSegments(edgeGeo, new THREE.LineBasicMaterial({
      color: 0x667788,
    }));
    this.surfaceGroup.add(line);
  }

  _renderRebarGroup(g) {
    const colorHex = parseInt(g.color.replace('#', ''), 16);

    g.bars.forEach(bar => {
      const start = new THREE.Vector3(...bar.start);
      const end = new THREE.Vector3(...bar.end);
      const dir = new THREE.Vector3().subVectors(end, start);
      const length = dir.length();
      if (length < 0.01) return;

      const radius = (g.diameter / 2) * 1.5;
      const mat = new THREE.MeshPhongMaterial({ color: colorHex });

      // Main bar cylinder
      const geo = new THREE.CylinderGeometry(radius, radius, length, 8);
      const mesh = new THREE.Mesh(geo, mat.clone());
      mesh.userData.groupId = g.id;
      mesh.userData.originalColor = colorHex;

      const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
      mesh.position.copy(mid);

      const yAxis = new THREE.Vector3(0, 1, 0);
      const barDir = dir.clone().normalize();
      const quat = new THREE.Quaternion().setFromUnitVectors(yAxis, barDir);
      mesh.quaternion.copy(quat);

      this.rebarGroup.add(mesh);

      // Hook stubs for straight bars
      if (g.shape === 'straight') {
        if (g.start_hook && g.start_hook !== 'none' && g.start_hook_ext > 0) {
          this._renderHookStub(start, barDir, radius, g.start_hook, g.start_hook_ext, colorHex, g.id, true);
        }
        if (g.end_hook && g.end_hook !== 'none' && g.end_hook_ext > 0) {
          this._renderHookStub(end, barDir, radius, g.end_hook, g.end_hook_ext, colorHex, g.id, false);
        }
      }
    });
  }

  _renderHookStub(point, barDir, radius, hookType, hookExtInches, colorHex, groupId, isStart) {
    // Use the actual ACI extension length from the API
    const hookLen = hookExtInches;
    if (hookLen <= 0) return;

    // Find a perpendicular direction for the hook bend
    // Prefer downward (negative Y) for hooks — typical structural convention
    const up = new THREE.Vector3(0, 1, 0);
    let perpDir = new THREE.Vector3().crossVectors(barDir, up);
    if (perpDir.length() < 0.01) {
      perpDir = new THREE.Vector3().crossVectors(barDir, new THREE.Vector3(1, 0, 0));
    }
    perpDir.normalize();
    // Point hook downward (toward negative Y if possible)
    if (perpDir.y > 0) perpDir.negate();

    let hookDir;
    if (hookType === '180_standard') {
      // 180-deg hook bends back along the bar direction
      hookDir = barDir.clone().multiplyScalar(isStart ? 1 : -1);
    } else if (hookType === '135_seismic') {
      // 135-deg hook: angled 45 degrees back toward the bar
      hookDir = perpDir.clone();
      const backDir = barDir.clone().multiplyScalar(isStart ? 1 : -1);
      hookDir.add(backDir).normalize();
    } else {
      // 90-deg hook: perpendicular to the bar
      hookDir = perpDir.clone();
    }

    const hookStart = point.clone();
    const hookEnd = hookStart.clone().add(hookDir.clone().multiplyScalar(hookLen));

    const hookMid = new THREE.Vector3().addVectors(hookStart, hookEnd).multiplyScalar(0.5);
    const hookGeo = new THREE.CylinderGeometry(radius, radius, hookLen, 8);
    const hookMat = new THREE.MeshPhongMaterial({ color: colorHex });
    const hookMesh = new THREE.Mesh(hookGeo, hookMat);
    hookMesh.userData.groupId = groupId;
    hookMesh.userData.originalColor = colorHex;
    hookMesh.position.copy(hookMid);

    const yAxis = new THREE.Vector3(0, 1, 0);
    const hDir = new THREE.Vector3().subVectors(hookEnd, hookStart).normalize();
    const hQuat = new THREE.Quaternion().setFromUnitVectors(yAxis, hDir);
    hookMesh.quaternion.copy(hQuat);

    this.rebarGroup.add(hookMesh);
  }

  zoomExtents() {
    this._fitCamera(this._lastBounds);
  }

  _fitCamera(bounds) {
    if (!bounds) return;
    this._lastBounds = bounds;
    const min = new THREE.Vector3(...bounds.min);
    const max = new THREE.Vector3(...bounds.max);
    const center = new THREE.Vector3().addVectors(min, max).multiplyScalar(0.5);
    const size = new THREE.Vector3().subVectors(max, min);
    const maxDim = Math.max(size.x, size.y, size.z);
    const dist = maxDim * 1.8;

    this.camera.position.set(
      center.x + dist * 0.6,
      center.y + dist * 0.5,
      center.z + dist * 0.8
    );
    this.controls.target.copy(center);
    this.controls.update();
  }
}

// Export to global scope for use by app.js
window.RebarViewer3D = RebarViewer3D;
