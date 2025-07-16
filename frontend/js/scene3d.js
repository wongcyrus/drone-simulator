/**
 * Scene3D - Three.js scene management for RoboMaster TT 3D Simulator
 */

class Scene3D {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);

        if (!this.container) {
            throw new Error(`Container with id '${containerId}' not found`);
        }

        // Scene components
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;

        // Lighting
        this.ambientLight = null;
        this.directionalLight = null;

        // Scene helpers
        this.gridHelper = null;
        this.axesHelper = null;

        // Animation
        this.animationId = null;
        this.isAnimating = false;

        // Scene bounds (in cm, matching backend) - no underground
        this.sceneBounds = {
            x: 1000,  // ±500cm (left/right)
            y: 500,   // 0-500cm (ground level and above only)
            z: 1000   // ±500cm (forward/back)
        };

        this.init();
    }

    init() {
        this.createScene();
        this.createCamera();
        this.createRenderer();
        this.createLighting();
        this.createHelpers();
        this.createControls();
        this.setupEventListeners();

        console.log('Scene3D initialized successfully');
    }

    createScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1a1a); // Dark background
        this.scene.fog = new THREE.Fog(0x1a1a1a, 1000, 3000); // Add some atmospheric fog
    }

    createCamera() {
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(75, aspect, 1, 5000);

        // Position camera for good initial view - closer to the scene
        this.camera.position.set(400, 300, 400);
        this.camera.lookAt(0, 100, 0); // Look at center, slightly elevated
    }

    createRenderer() {
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true
        });

        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);

        // Enable shadows for more realistic rendering
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        // Tone mapping for better lighting
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.0;

        this.container.appendChild(this.renderer.domElement);
    }

    createLighting() {
        // Ambient light for general illumination
        this.ambientLight = new THREE.AmbientLight(0x404040, 0.4); // Soft white light
        this.scene.add(this.ambientLight);

        // Directional light (like sunlight)
        this.directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        this.directionalLight.position.set(500, 1000, 500);
        this.directionalLight.castShadow = true;

        // Configure shadow properties
        this.directionalLight.shadow.mapSize.width = 2048;
        this.directionalLight.shadow.mapSize.height = 2048;
        this.directionalLight.shadow.camera.near = 0.5;
        this.directionalLight.shadow.camera.far = 3000;
        this.directionalLight.shadow.camera.left = -1000;
        this.directionalLight.shadow.camera.right = 1000;
        this.directionalLight.shadow.camera.top = 1000;
        this.directionalLight.shadow.camera.bottom = -1000;

        this.scene.add(this.directionalLight);

        // Add a subtle fill light from the opposite direction
        const fillLight = new THREE.DirectionalLight(0x4080ff, 0.2);
        fillLight.position.set(-500, 500, -500);
        this.scene.add(fillLight);
    }

    createHelpers() {
        // Grid helper for ground plane
        const gridSize = Math.max(this.sceneBounds.x, this.sceneBounds.y);
        const gridDivisions = 20;

        this.gridHelper = new THREE.GridHelper(
            gridSize,
            gridDivisions,
            0x444444,  // Center line color
            0x222222   // Grid line color
        );
        this.gridHelper.position.y = 0;
        this.scene.add(this.gridHelper);

        // Axes helper for coordinate system reference
        this.axesHelper = new THREE.AxesHelper(200);
        this.axesHelper.position.set(0, 0, 0);
        this.scene.add(this.axesHelper);

        // Add boundary box to visualize scene limits
        this.createBoundaryBox();

        // Add ground plane
        this.createGroundPlane();
    }

    createBoundaryBox() {
        const geometry = new THREE.BoxGeometry(
            this.sceneBounds.x,
            this.sceneBounds.y,
            this.sceneBounds.z
        );

        const edges = new THREE.EdgesGeometry(geometry);
        const material = new THREE.LineBasicMaterial({
            color: 0x666666,
            transparent: true,
            opacity: 0.3
        });

        const boundaryBox = new THREE.LineSegments(edges, material);
        // Position box so bottom is at ground level (y=0) and top is at max height
        // Box center should be at y = sceneBounds.y / 2 to cover 0 to sceneBounds.y
        boundaryBox.position.set(0, this.sceneBounds.y / 2, 0);
        this.scene.add(boundaryBox);
    }

    createGroundPlane() {
        const geometry = new THREE.PlaneGeometry(
            this.sceneBounds.x,
            this.sceneBounds.z
        );

        const material = new THREE.MeshLambertMaterial({
            color: 0x2a2a2a,
            transparent: true,
            opacity: 0.8
        });

        const groundPlane = new THREE.Mesh(geometry, material);
        groundPlane.rotation.x = -Math.PI / 2; // Rotate to be horizontal
        groundPlane.position.y = 0;
        groundPlane.receiveShadow = true;

        this.scene.add(groundPlane);
    }

    createControls() {
        if (!THREE.OrbitControls) {
            console.warn('OrbitControls not available');
            return;
        }

        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);

        // Configure controls
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;

        // Set limits
        this.controls.minDistance = 100;
        this.controls.maxDistance = 2000;
        this.controls.maxPolarAngle = Math.PI / 2; // Don't allow camera to go below ground

        // Set target to center of scene
        this.controls.target.set(0, 100, 0);
        this.controls.update();
    }

    setupEventListeners() {
        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize(), false);

        // Handle container resize (if using ResizeObserver)
        if (window.ResizeObserver) {
            const resizeObserver = new ResizeObserver(() => this.onWindowResize());
            resizeObserver.observe(this.container);
        }
    }

    onWindowResize() {
        if (!this.camera || !this.renderer) return;

        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
    }

    render() {
        if (!this.renderer || !this.scene || !this.camera) return;

        // Update controls if available
        if (this.controls) {
            this.controls.update();
        }

        // Render the scene
        this.renderer.render(this.scene, this.camera);
    }

    startAnimation() {
        if (this.isAnimating) return;

        this.isAnimating = true;
        this.animate();
    }

    stopAnimation() {
        this.isAnimating = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    animate() {
        if (!this.isAnimating) return;

        this.animationId = requestAnimationFrame(() => this.animate());
        this.render();
    }

    // Utility methods for coordinate conversion
    worldToScreen(worldPosition) {
        const vector = worldPosition.clone();
        vector.project(this.camera);

        const x = (vector.x * 0.5 + 0.5) * this.container.clientWidth;
        const y = (vector.y * -0.5 + 0.5) * this.container.clientHeight;

        return { x, y };
    }

    screenToWorld(screenX, screenY, z = 0) {
        const vector = new THREE.Vector3();
        vector.set(
            (screenX / this.container.clientWidth) * 2 - 1,
            -(screenY / this.container.clientHeight) * 2 + 1,
            0.5
        );

        vector.unproject(this.camera);

        const dir = vector.sub(this.camera.position).normalize();
        const distance = (z - this.camera.position.z) / dir.z;

        return this.camera.position.clone().add(dir.multiplyScalar(distance));
    }

    // Scene management methods
    addObject(object) {
        this.scene.add(object);
    }

    removeObject(object) {
        this.scene.remove(object);
    }

    getObjectByName(name) {
        return this.scene.getObjectByName(name);
    }

    // Camera control methods
    setCameraPosition(x, y, z) {
        this.camera.position.set(x, y, z);
        if (this.controls) {
            this.controls.update();
        }
    }

    setCameraTarget(x, y, z) {
        if (this.controls) {
            this.controls.target.set(x, y, z);
            this.controls.update();
        }
    }

    resetCamera() {
        this.setCameraPosition(400, 300, 400);
        this.setCameraTarget(0, 100, 0);
    }

    // Cleanup
    dispose() {
        this.stopAnimation();

        if (this.controls) {
            this.controls.dispose();
        }

        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
        }

        // Clean up geometries and materials
        this.scene.traverse((object) => {
            if (object.geometry) {
                object.geometry.dispose();
            }
            if (object.material) {
                if (Array.isArray(object.material)) {
                    object.material.forEach(material => material.dispose());
                } else {
                    object.material.dispose();
                }
            }
        });

        console.log('Scene3D disposed');
    }
}