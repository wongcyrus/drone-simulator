/**
 * DroneRenderer - Handles 3D drone model creation and animation
 */

class DroneRenderer {
    constructor(scene3d) {
        this.scene3d = scene3d;
        this.drones = new Map(); // droneId -> drone3DObject
        
        // Drone model parameters
        this.droneSize = {
            body: { width: 20, height: 8, depth: 20 },
            propeller: { radius: 8, height: 2 },
            arm: { length: 15, width: 3, height: 2 }
        };
        
        // Colors for different drone states
        this.colors = {
            body: {
                connected: 0x4CAF50,    // Green
                disconnected: 0x757575, // Gray
                flying: 0x2196F3,       // Blue
                error: 0xf44336         // Red
            },
            propeller: 0x333333,
            arm: 0x666666,
            label: 0xffffff
        };
        
        // Animation properties
        this.propellerRotationSpeed = 0.3; // radians per frame
        this.animations = new Map(); // droneId -> animation data
        
        // Movement interpolation
        this.interpolationSpeed = 0.1; // Smoothing factor for position updates
        this.targetPositions = new Map(); // droneId -> target position
        this.targetRotations = new Map(); // droneId -> target rotation
        
        // Animation states
        this.animationStates = new Map(); // droneId -> animation state
        
        console.log('DroneRenderer initialized');
    }
    
    addDrone(droneId, droneState) {
        if (this.drones.has(droneId)) {
            console.warn(`Drone ${droneId} already exists, updating instead`);
            this.updateDrone(droneId, droneState);
            return;
        }
        
        const drone3D = this.createDroneModel(droneId, droneState);
        this.drones.set(droneId, drone3D);
        this.scene3d.addObject(drone3D);
        
        // Set initial position
        this.updateDronePosition(droneId, droneState);
        
        console.log(`Added 3D drone: ${droneId}`);
    }
    
    updateDrone(droneId, droneState) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) {
            console.warn(`Drone ${droneId} not found for update`);
            return;
        }
        
        // Update position and rotation
        this.updateDronePosition(droneId, droneState);
        this.updateDroneAppearance(droneId, droneState);
        this.updateDroneLabel(droneId, droneState);
    }
    
    removeDrone(droneId) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) {
            console.warn(`Drone ${droneId} not found for removal`);
            return;
        }
        
        // Remove from scene
        this.scene3d.removeObject(drone3D);
        
        // Clean up geometries and materials
        this.disposeDroneModel(drone3D);
        
        // Remove from maps
        this.drones.delete(droneId);
        this.animations.delete(droneId);
        
        console.log(`Removed 3D drone: ${droneId}`);
    }
    
    createDroneModel(droneId, droneState) {
        const droneGroup = new THREE.Group();
        droneGroup.name = `drone_${droneId}`;
        
        // Create drone body
        const bodyGeometry = new THREE.BoxGeometry(
            this.droneSize.body.width,
            this.droneSize.body.height,
            this.droneSize.body.depth
        );
        
        const bodyMaterial = new THREE.MeshLambertMaterial({
            color: this.getDroneColor(droneState)
        });
        
        const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
        body.castShadow = true;
        body.receiveShadow = true;
        body.name = 'body';
        droneGroup.add(body);
        
        // Create arms and propellers
        this.createArmsAndPropellers(droneGroup);
        
        // Create drone label
        this.createDroneLabel(droneGroup, droneId, droneState);
        
        // Create status indicator
        this.createStatusIndicator(droneGroup, droneState);
        
        return droneGroup;
    }
    
    createArmsAndPropellers(droneGroup) {
        const armPositions = [
            { x: 12, z: 12 },   // Front right
            { x: -12, z: 12 },  // Front left
            { x: -12, z: -12 }, // Back left
            { x: 12, z: -12 }   // Back right
        ];
        
        const propellersGroup = new THREE.Group();
        propellersGroup.name = 'propellers';
        
        armPositions.forEach((pos, index) => {
            // Create arm
            const armGeometry = new THREE.BoxGeometry(
                this.droneSize.arm.width,
                this.droneSize.arm.height,
                this.droneSize.arm.length
            );
            
            const armMaterial = new THREE.MeshLambertMaterial({
                color: this.colors.arm
            });
            
            const arm = new THREE.Mesh(armGeometry, armMaterial);
            arm.position.set(pos.x * 0.7, 0, pos.z * 0.7);
            arm.castShadow = true;
            droneGroup.add(arm);
            
            // Create propeller
            const propellerGeometry = new THREE.CylinderGeometry(
                this.droneSize.propeller.radius,
                this.droneSize.propeller.radius,
                this.droneSize.propeller.height,
                8
            );
            
            const propellerMaterial = new THREE.MeshLambertMaterial({
                color: this.colors.propeller,
                transparent: true,
                opacity: 0.7
            });
            
            const propeller = new THREE.Mesh(propellerGeometry, propellerMaterial);
            propeller.position.set(pos.x, this.droneSize.body.height / 2 + 2, pos.z);
            propeller.name = `propeller_${index}`;
            propellersGroup.add(propeller);
        });
        
        droneGroup.add(propellersGroup);
    }
    
    createDroneLabel(droneGroup, droneId, droneState) {
        // Create text texture
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 256;
        canvas.height = 64;
        
        // Draw label background
        context.fillStyle = 'rgba(0, 0, 0, 0.8)';
        context.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw text
        context.fillStyle = '#ffffff';
        context.font = 'bold 20px Arial';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(droneId, canvas.width / 2, canvas.height / 2 - 8);
        
        // Draw port info
        context.font = '14px Arial';
        context.fillText(`Port: ${droneState.udp_port}`, canvas.width / 2, canvas.height / 2 + 12);
        
        // Create sprite
        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(spriteMaterial);
        
        sprite.position.set(0, 25, 0); // Above the drone
        sprite.scale.set(40, 10, 1);
        sprite.name = 'label';
        
        droneGroup.add(sprite);
    }
    
    createStatusIndicator(droneGroup, droneState) {
        // Create a small sphere to indicate status
        const indicatorGeometry = new THREE.SphereGeometry(2, 8, 8);
        const indicatorMaterial = new THREE.MeshBasicMaterial({
            color: droneState.is_flying ? 0x00ff00 : 0xff0000
        });
        
        const indicator = new THREE.Mesh(indicatorGeometry, indicatorMaterial);
        indicator.position.set(0, this.droneSize.body.height / 2 + 5, 0);
        indicator.name = 'status_indicator';
        
        droneGroup.add(indicator);
    }
    
    updateDronePosition(droneId, droneState) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return;
        
        // Convert backend coordinates to Three.js coordinates
        const targetPosition = new THREE.Vector3(
            droneState.position.x,
            droneState.position.z, // Z becomes Y in Three.js
            -droneState.position.y // Y becomes -Z in Three.js (flip for correct orientation)
        );
        
        const targetRotation = new THREE.Euler(
            THREE.MathUtils.degToRad(droneState.rotation.x), // Pitch
            THREE.MathUtils.degToRad(droneState.rotation.z), // Yaw
            THREE.MathUtils.degToRad(droneState.rotation.y)  // Roll
        );
        
        // Store target positions for smooth interpolation
        this.targetPositions.set(droneId, targetPosition);
        this.targetRotations.set(droneId, targetRotation);
        
        // If this is the first update, set position immediately
        if (!this.animationStates.has(droneId)) {
            drone3D.position.copy(targetPosition);
            drone3D.rotation.copy(targetRotation);
            this.animationStates.set(droneId, {
                lastPosition: targetPosition.clone(),
                lastRotation: targetRotation.clone(),
                isMoving: false,
                movementStartTime: 0
            });
        }
    }
    
    updateDroneAppearance(droneId, droneState) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return;
        
        // Update body color based on state
        const body = drone3D.getObjectByName('body');
        if (body && body.material) {
            body.material.color.setHex(this.getDroneColor(droneState));
        }
        
        // Update status indicator
        const statusIndicator = drone3D.getObjectByName('status_indicator');
        if (statusIndicator && statusIndicator.material) {
            statusIndicator.material.color.setHex(
                droneState.is_flying ? 0x00ff00 : 0xff0000
            );
        }
        
        // Update propeller visibility based on flying state
        const propellersGroup = drone3D.getObjectByName('propellers');
        if (propellersGroup) {
            propellersGroup.children.forEach(propeller => {
                if (propeller.material) {
                    propeller.material.opacity = droneState.is_flying ? 0.3 : 0.7;
                }
            });
        }
    }
    
    updateDroneLabel(droneId, droneState) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return;
        
        const label = drone3D.getObjectByName('label');
        if (!label || !label.material || !label.material.map) return;
        
        // Update label texture
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 256;
        canvas.height = 64;
        
        // Draw label background
        context.fillStyle = 'rgba(0, 0, 0, 0.8)';
        context.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw text
        context.fillStyle = '#ffffff';
        context.font = 'bold 20px Arial';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(droneId, canvas.width / 2, canvas.height / 2 - 8);
        
        // Draw battery level
        const batteryColor = droneState.battery > 50 ? '#4CAF50' : 
                           droneState.battery > 20 ? '#FF9800' : '#f44336';
        context.fillStyle = batteryColor;
        context.font = '14px Arial';
        context.fillText(`${droneState.battery}%`, canvas.width / 2, canvas.height / 2 + 12);
        
        // Update texture
        const texture = new THREE.CanvasTexture(canvas);
        label.material.map = texture;
        label.material.needsUpdate = true;
    }
    
    getDroneColor(droneState) {
        if (!droneState.is_connected) {
            return this.colors.body.disconnected;
        } else if (droneState.is_flying) {
            return this.colors.body.flying;
        } else {
            return this.colors.body.connected;
        }
    }
    
    // Animation methods
    update() {
        // Update all drone animations
        this.drones.forEach((drone3D, droneId) => {
            this.updateDroneAnimations(drone3D, droneId);
        });
    }
    
    updateDroneAnimations(drone3D, droneId) {
        // Update position interpolation
        this.updatePositionInterpolation(drone3D, droneId);
        
        // Update propeller animations
        this.updatePropellerAnimation(drone3D, droneId);
        
        // Update movement effects
        this.updateMovementEffects(drone3D, droneId);
    }
    
    updatePositionInterpolation(drone3D, droneId) {
        const targetPosition = this.targetPositions.get(droneId);
        const targetRotation = this.targetRotations.get(droneId);
        const animationState = this.animationStates.get(droneId);
        
        if (!targetPosition || !targetRotation || !animationState) return;
        
        // Smooth position interpolation
        const currentPosition = drone3D.position;
        const positionDistance = currentPosition.distanceTo(targetPosition);
        
        if (positionDistance > 0.1) { // Only interpolate if there's significant movement
            // Use lerp for smooth movement
            currentPosition.lerp(targetPosition, this.interpolationSpeed);
            
            // Update movement state
            if (!animationState.isMoving) {
                animationState.isMoving = true;
                animationState.movementStartTime = Date.now();
            }
        } else {
            // Snap to target if very close
            currentPosition.copy(targetPosition);
            animationState.isMoving = false;
        }
        
        // Smooth rotation interpolation
        const currentRotation = drone3D.rotation;
        const rotationDistance = Math.abs(currentRotation.x - targetRotation.x) + 
                                Math.abs(currentRotation.y - targetRotation.y) + 
                                Math.abs(currentRotation.z - targetRotation.z);
        
        if (rotationDistance > 0.01) {
            // Interpolate rotation
            currentRotation.x = THREE.MathUtils.lerp(currentRotation.x, targetRotation.x, this.interpolationSpeed);
            currentRotation.y = THREE.MathUtils.lerp(currentRotation.y, targetRotation.y, this.interpolationSpeed);
            currentRotation.z = THREE.MathUtils.lerp(currentRotation.z, targetRotation.z, this.interpolationSpeed);
        } else {
            // Snap to target rotation if very close
            currentRotation.copy(targetRotation);
        }
        
        // Update last known positions
        animationState.lastPosition.copy(currentPosition);
        animationState.lastRotation.copy(currentRotation);
    }
    
    updateMovementEffects(drone3D, droneId) {
        const animationState = this.animationStates.get(droneId);
        if (!animationState) return;
        
        // Check for special animations
        const specialAnimation = this.animations.get(droneId);
        if (specialAnimation) {
            this.updateSpecialAnimation(drone3D, droneId, specialAnimation);
            return;
        }
        
        // Add subtle bobbing effect when hovering
        if (!animationState.isMoving && drone3D.position.y > 10) {
            const time = Date.now() * 0.001; // Convert to seconds
            const bobAmount = Math.sin(time * 2) * 0.5; // Small bobbing motion
            drone3D.position.y += bobAmount * 0.1; // Very subtle effect
        }
        
        // Add banking effect during turns
        const targetRotation = this.targetRotations.get(droneId);
        if (targetRotation && animationState.isMoving) {
            const rotationSpeed = Math.abs(drone3D.rotation.y - targetRotation.y);
            const bankAngle = Math.min(rotationSpeed * 2, Math.PI / 6); // Max 30 degrees
            
            // Apply banking to roll
            if (drone3D.rotation.y > targetRotation.y) {
                drone3D.rotation.z = THREE.MathUtils.lerp(drone3D.rotation.z, -bankAngle, 0.1);
            } else if (drone3D.rotation.y < targetRotation.y) {
                drone3D.rotation.z = THREE.MathUtils.lerp(drone3D.rotation.z, bankAngle, 0.1);
            } else {
                drone3D.rotation.z = THREE.MathUtils.lerp(drone3D.rotation.z, 0, 0.1);
            }
        }
    }
    
    updateSpecialAnimation(drone3D, droneId, animation) {
        const currentTime = Date.now();
        const elapsed = currentTime - animation.startTime;
        const progress = Math.min(elapsed / animation.duration, 1.0);
        
        switch (animation.type) {
            case 'takeoff':
                this.updateTakeoffAnimation(drone3D, animation, progress);
                break;
            case 'landing':
                this.updateLandingAnimation(drone3D, animation, progress);
                break;
            case 'flip':
                this.updateFlipAnimation(drone3D, animation, progress);
                break;
        }
        
        // Remove animation when complete
        if (progress >= 1.0) {
            this.animations.delete(droneId);
        }
    }
    
    updateTakeoffAnimation(drone3D, animation, progress) {
        // Smooth takeoff with slight wobble
        const easeProgress = this.easeOutCubic(progress);
        const wobble = Math.sin(progress * Math.PI * 4) * 2 * (1 - progress);
        
        drone3D.position.y = animation.startY + (animation.targetY - animation.startY) * easeProgress + wobble;
        
        // Add slight rotation during takeoff
        drone3D.rotation.z = Math.sin(progress * Math.PI * 2) * 0.05 * (1 - progress);
    }
    
    updateLandingAnimation(drone3D, animation, progress) {
        // Smooth landing with deceleration
        const easeProgress = this.easeInCubic(progress);
        
        drone3D.position.y = animation.startY + (animation.targetY - animation.startY) * easeProgress;
        
        // Add slight settling motion
        if (progress > 0.8) {
            const settleProgress = (progress - 0.8) / 0.2;
            const settle = Math.sin(settleProgress * Math.PI * 6) * 1 * (1 - settleProgress);
            drone3D.position.y += settle;
        }
    }
    
    updateFlipAnimation(drone3D, animation, progress) {
        // Flip animation with height gain
        const flipProgress = this.easeInOutCubic(progress);
        
        // Rotation for flip
        if (animation.axis === 'x') {
            drone3D.rotation.x = animation.startRotation.x + animation.rotationAmount * flipProgress;
        } else if (animation.axis === 'y') {
            drone3D.rotation.y = animation.startRotation.y + animation.rotationAmount * flipProgress;
        } else {
            drone3D.rotation.z = animation.startRotation.z + animation.rotationAmount * flipProgress;
        }
        
        // Height change during flip (parabolic)
        const heightMultiplier = 4 * progress * (1 - progress); // Parabola
        drone3D.position.y = animation.startY + animation.heightGain * heightMultiplier;
    }
    
    // Easing functions
    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }
    
    easeInCubic(t) {
        return t * t * t;
    }
    
    easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }
    
    // Special animation triggers
    startTakeoffAnimation(droneId) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return;
        
        this.animations.set(droneId, {
            type: 'takeoff',
            startTime: Date.now(),
            duration: 2000, // 2 seconds
            startY: drone3D.position.y,
            targetY: drone3D.position.y + 100 // Rise 100cm
        });
    }
    
    startLandingAnimation(droneId) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return;
        
        this.animations.set(droneId, {
            type: 'landing',
            startTime: Date.now(),
            duration: 2500, // 2.5 seconds
            startY: drone3D.position.y,
            targetY: 0 // Land at ground level
        });
    }
    
    startFlipAnimation(droneId, direction) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return;
        
        const axisMap = {
            'l': 'y', 'r': 'y', // Left/right flips around Y axis
            'f': 'x', 'b': 'x'  // Forward/back flips around X axis
        };
        
        const rotationMap = {
            'l': Math.PI * 2,   // 360 degrees left
            'r': -Math.PI * 2,  // 360 degrees right
            'f': Math.PI * 2,   // 360 degrees forward
            'b': -Math.PI * 2   // 360 degrees back
        };
        
        this.animations.set(droneId, {
            type: 'flip',
            startTime: Date.now(),
            duration: 1000, // 1 second
            axis: axisMap[direction] || 'y',
            rotationAmount: rotationMap[direction] || Math.PI * 2,
            startRotation: {
                x: drone3D.rotation.x,
                y: drone3D.rotation.y,
                z: drone3D.rotation.z
            },
            startY: drone3D.position.y,
            heightGain: 20 // Gain 20cm height during flip
        });
    }
    
    updatePropellerAnimation(drone3D, droneId) {
        const propellersGroup = drone3D.getObjectByName('propellers');
        if (!propellersGroup) return;
        
        // Get drone state to determine if propellers should spin
        const droneState = this.getDroneState(droneId);
        const shouldSpin = droneState && droneState.is_flying;
        
        propellersGroup.children.forEach((propeller, index) => {
            if (shouldSpin) {
                // Alternate rotation direction for realism
                const direction = (index % 2 === 0) ? 1 : -1;
                propeller.rotation.y += this.propellerRotationSpeed * direction;
            }
        });
    }
    
    getDroneState(droneId) {
        // This would typically come from the main application
        // For now, we'll assume flying state based on position
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return null;
        
        return {
            is_flying: drone3D.position.y > 5 // Assume flying if above 5cm
        };
    }
    
    // Utility methods
    getDronePosition(droneId) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return null;
        
        return {
            x: drone3D.position.x,
            y: -drone3D.position.z, // Convert back to backend coordinates
            z: drone3D.position.y
        };
    }
    
    highlightDrone(droneId, duration = 2000) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return;
        
        const body = drone3D.getObjectByName('body');
        if (!body || !body.material) return;
        
        // Store original color
        const originalColor = body.material.color.getHex();
        
        // Set highlight color
        body.material.color.setHex(0xffff00); // Yellow highlight
        
        // Restore original color after duration
        setTimeout(() => {
            if (body.material) {
                body.material.color.setHex(originalColor);
            }
        }, duration);
    }
    
    focusOnDrone(droneId) {
        const drone3D = this.drones.get(droneId);
        if (!drone3D) return;
        
        // Set camera to focus on this drone
        this.scene3d.setCameraTarget(
            drone3D.position.x,
            drone3D.position.y,
            drone3D.position.z
        );
    }
    
    // Cleanup methods
    disposeDroneModel(drone3D) {
        drone3D.traverse((object) => {
            if (object.geometry) {
                object.geometry.dispose();
            }
            if (object.material) {
                if (Array.isArray(object.material)) {
                    object.material.forEach(material => {
                        if (material.map) material.map.dispose();
                        material.dispose();
                    });
                } else {
                    if (object.material.map) object.material.map.dispose();
                    object.material.dispose();
                }
            }
        });
    }
    
    dispose() {
        // Remove all drones
        this.drones.forEach((drone3D, droneId) => {
            this.removeDrone(droneId);
        });
        
        this.drones.clear();
        this.animations.clear();
        
        console.log('DroneRenderer disposed');
    }
}