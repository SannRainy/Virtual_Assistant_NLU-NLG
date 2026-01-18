<script>
  import { onMount } from 'svelte';
  import * as THREE from 'three';
  import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
  import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
  import { getBehaviorForEmotion } from '../utils/behaviors.js';

  export let isSpeaking = false;
  export let emotion = 'neutral';
  export let mouthCues = { a: 0, i: 0, u: 0, e: 0, o: 0 };

  let canvasContainer;
  let currentVrm = null;
  let renderer, scene, camera, clock;
  let animationFrameId;

  let idleTimer = 0;
  let timeToNextIdleAction = 7.5; 
  let activeBehavior = null;
  let behaviorTimer = 0;

  let blinkTimer = 0;
  let isBlinking = false;
  let nextBlinkTime = 2.5;
  let blinkPhase = 'idle';
  let blinkProgress = 0;
  let blinkHold = 0;
  let blinksRemaining = 0;

  let mouse = { x: 0, y: 0 };
  let gazeTimer = 0;
  let gazeTarget = { x: 0, y: 0 };
  let smoothedGaze = { x: 0, y: 0 };
  let boneCache = new Map();

  let targets = {
    blink: 0, joy: 0, surprised: 0, oh: 0, sorrow: 0, fun: 0, 
    aa: 0, ih: 0, ou: 0, ee: 0, oh_mouth: 0,
    
    hips: new THREE.Euler(0, 0, 0),
    neck: new THREE.Euler(0, 0, 0),
    head: new THREE.Euler(0, 0, 0),
    chest: new THREE.Euler(0, 0, 0),
    spine: new THREE.Euler(0, 0, 0),
    leftShoulder: new THREE.Euler(0, 0, 0),
    rightShoulder: new THREE.Euler(0, 0, 0),
    
    leftEye: new THREE.Euler(0, 0, 0),
    rightEye: new THREE.Euler(0, 0, 0),

    leftUpperArm: new THREE.Euler(0, 0, -1.25), 
    leftLowerArm: new THREE.Euler(0, 0, 0),
    leftHand: new THREE.Euler(0, 0, 0),
    
    rightUpperArm: new THREE.Euler(0, 0, 1.25), 
    rightLowerArm: new THREE.Euler(0, 0, 0),
    rightHand: new THREE.Euler(0, 0, 0),

    leftHandPose: 0.05,
    rightHandPose: 0.05
  };

  const lerp = (start, end, factor) => {
    return start + (end - start) * factor;
  };

  const clamp01 = (v) => Math.max(0, Math.min(1, v));
  const easeInCubic = (t) => t * t * t;
  const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
  const BLINK_MAX = 1.0;

  const updateLogic = (deltaTime) => {
    if (!currentVrm) return;
    const elapsedTime = clock.elapsedTime;

    if (isSpeaking) {
      activeBehavior = null;
      behaviorTimer = 0;
      idleTimer = 0;
    } else {
      idleTimer += deltaTime;
      if (activeBehavior) {
        behaviorTimer += deltaTime;
        if (behaviorTimer >= activeBehavior.duration) {
          activeBehavior = null;
          behaviorTimer = 0;
          idleTimer = 0;
          timeToNextIdleAction = 6.0 + Math.random() * 10.0;
        }
      } else if (idleTimer >= timeToNextIdleAction) {
        activeBehavior = getBehaviorForEmotion(emotion);
        behaviorTimer = 0;
        idleTimer = 0;
        timeToNextIdleAction = 6.0 + Math.random() * 10.0;
      }
    }

    let behaviorOut = null;
    if (activeBehavior) {
      const p = Math.min(1, behaviorTimer / Math.max(0.001, activeBehavior.duration));
      behaviorOut = activeBehavior.apply(currentVrm, p);
    }

    nextBlinkTime -= deltaTime;
    if (blinkPhase === 'idle' && nextBlinkTime <= 0) {
      const isDouble = Math.random() < 0.18;
      blinksRemaining = isDouble ? 2 : 1;
      blinkPhase = 'closing';
      blinkProgress = 0;
      blinkHold = 0;
      isBlinking = true;
    }

    if (blinkPhase === 'closing') {
      const closeDur = 0.06;
      blinkProgress = Math.min(1, blinkProgress + deltaTime / closeDur);
      targets.blink = clamp01(easeInCubic(blinkProgress) * BLINK_MAX);
      if (blinkProgress >= 1) {
        blinkPhase = 'closed';
        blinkHold = 0.03;
        blinkProgress = 0;
      }
    } else if (blinkPhase === 'closed') {
      targets.blink = BLINK_MAX;
      blinkHold -= deltaTime;
      if (blinkHold <= 0) {
        blinkPhase = 'opening';
        blinkProgress = 0;
      }
    } else if (blinkPhase === 'opening') {
      const openDur = 0.10;
      blinkProgress = Math.min(1, blinkProgress + deltaTime / openDur);
      targets.blink = clamp01((1 - easeOutCubic(blinkProgress)) * BLINK_MAX);
      if (blinkProgress >= 1) {
        blinksRemaining = Math.max(0, blinksRemaining - 1);
        if (blinksRemaining > 0) {
          blinkPhase = 'closing';
          blinkProgress = 0;
          blinkHold = 0;
        } else {
          blinkPhase = 'idle';
          blinkProgress = 0;
          blinkHold = 0;
          isBlinking = false;
          nextBlinkTime = Math.random() * 3.5 + 1.8;
          targets.blink = 0;
        }
      }
    } else {
      targets.blink = 0;
    }

    const breath = Math.sin(elapsedTime * 1.05) * 0.03;
    const sway = Math.sin(elapsedTime * 0.45) * 0.02;
    const sway2 = Math.sin(elapsedTime * 0.7 + 1.2) * 0.012;
    targets.hips.set(sway2 * 0.35, sway * 0.25, sway2 * 0.15);
    targets.spine.set(sway2 * 0.25, 0, sway * 0.12);
    targets.chest.set(breath + sway2 * 0.12, sway * 0.12, sway2 * 0.18);

    gazeTimer -= deltaTime;
    if (gazeTimer <= 0) {
      gazeTimer = 1.0 + Math.random() * 2.5;
      gazeTarget = {
        x: (Math.random() * 2 - 1) * 0.35,
        y: (Math.random() * 2 - 1) * 0.35
      };
    }
    const gazeSmooth = 1.0 - Math.exp(-7.0 * deltaTime);
    const combinedGazeX = mouse.x * 0.8 + gazeTarget.x * 0.2;
    const combinedGazeY = mouse.y * 0.8 + gazeTarget.y * 0.2;
    smoothedGaze.x = lerp(smoothedGaze.x, combinedGazeX, gazeSmooth);
    smoothedGaze.y = lerp(smoothedGaze.y, combinedGazeY, gazeSmooth);

    const eyeLookX = -smoothedGaze.y * 0.05; 
    const eyeLookY = smoothedGaze.x * 0.05; 
    const headLookX = -smoothedGaze.y * 0.05;
    const headLookY = smoothedGaze.x * 0.05;

    targets.leftEye.set(eyeLookX, eyeLookY, 0);
    targets.rightEye.set(eyeLookX, eyeLookY, 0);

    targets.neck.set(headLookX * 0.5, headLookY * 0.5, 0);
    targets.head.set(headLookX * 0.5, headLookY * 0.5, 0);
    
    targets.leftShoulder.set(0, 0, 0);
    targets.rightShoulder.set(0, 0, 0);

    // FIXED STATIC ARM POSITIONS
    targets.leftUpperArm.set(0, 0, -1.25);
    targets.leftLowerArm.set(0, 0, 0);
    targets.leftHand.set(0, 0, 0);
    targets.leftHandPose = 0.05;

    targets.rightUpperArm.set(0, 0, 1.25);
    targets.rightLowerArm.set(0, 0, 0);
    targets.rightHand.set(0, 0, 0);
    targets.rightHandPose = 0.05;

    targets.joy = 0; targets.surprised = 0; targets.oh = 0; targets.sorrow = 0; targets.fun = 0;
    if (emotion === 'happy') {
        targets.joy += 0.4;
        targets.fun += 0.2;
        targets.chest.y += 0.03;
    } else if (emotion === 'sad') {
        targets.sorrow += 0.4;
        targets.chest.x += -0.05;
        targets.head.x += 0.04;
        targets.head.z += 0.06;
    } else if (emotion === 'surprised') {
        targets.surprised += 0.5;
        targets.head.x += -0.07;
        targets.chest.x += 0.1;
    } else if (emotion === 'confused') {
        targets.fun += 0.2;
        targets.head.z += 0.1;
    } else if (emotion === 'oh') {
        targets.oh += 0.5;
        targets.chest.x += 0.05;
    }

    if (behaviorOut) {
      targets.joy += behaviorOut.joy || 0;
      targets.fun += behaviorOut.fun || 0;
      targets.sorrow += behaviorOut.sorrow || 0;
      targets.surprised += behaviorOut.surprised || 0;
      targets.oh += behaviorOut.oh || 0;
      if (behaviorOut.blink !== undefined) {
        targets.blink = Math.max(targets.blink, clamp01(behaviorOut.blink));
      }
      if (behaviorOut.neckX) targets.neck.x += behaviorOut.neckX;
      if (behaviorOut.neckY) targets.neck.y += behaviorOut.neckY;
      if (behaviorOut.neckZ) targets.neck.z += behaviorOut.neckZ;
      if (behaviorOut.headX) targets.head.x += behaviorOut.headX;
      if (behaviorOut.headY) targets.head.y += behaviorOut.headY;
      if (behaviorOut.headZ) targets.head.z += behaviorOut.headZ;
      if (behaviorOut.chestX) targets.chest.x += behaviorOut.chestX;
      if (behaviorOut.chestY) targets.chest.y += behaviorOut.chestY;
      if (behaviorOut.chestZ) targets.chest.z += behaviorOut.chestZ;
      if (behaviorOut.spineY) targets.spine.y += behaviorOut.spineY;
    }

    const blinkIsolation = clamp01(1 - targets.blink);
    targets.joy *= blinkIsolation;
    targets.fun *= blinkIsolation;
    targets.surprised *= blinkIsolation;
    targets.sorrow *= blinkIsolation;
    targets.oh *= blinkIsolation;

    if (isSpeaking) {
        const speechSmooth = 1.0 - Math.exp(-25.0 * deltaTime); 
        
        targets.aa = lerp(currentVrm.expressionManager.getValue('aa'), mouthCues.a * 0.9, speechSmooth);
        targets.ih = lerp(currentVrm.expressionManager.getValue('ih'), mouthCues.i * 0.8, speechSmooth);
        targets.ou = lerp(currentVrm.expressionManager.getValue('ou'), mouthCues.u * 0.5, speechSmooth);
        targets.ee = lerp(currentVrm.expressionManager.getValue('ee'), mouthCues.e * 0.8, speechSmooth);
        targets.oh_mouth = lerp(currentVrm.expressionManager.getValue('oh'), mouthCues.o * 0.65, speechSmooth);
        
        const totalVol = mouthCues.a + mouthCues.i + mouthCues.u + mouthCues.e + mouthCues.o;
        targets.head.x += (Math.sin(elapsedTime * 4.0) * 0.02 + 0.01) * Math.min(1, totalVol);
        targets.chest.y += (Math.sin(elapsedTime * 3.0) * 0.015) * Math.min(1, totalVol);
    } else {
        const microMouth = (Math.sin(elapsedTime * 0.9) * 0.5 + 0.5) * 0.02;
        targets.aa = microMouth;
        targets.ih = 0; targets.ou = 0; targets.ee = 0; targets.oh_mouth = 0;
        
        if (!activeBehavior) {
          targets.fun += 0.03;
        }
    }
  };

  const applySmoothMovement = (deltaTime) => {
    if (!currentVrm) return;
    
    const speed = 5.0; 
    const smoothFactor = 1.0 - Math.exp(-speed * deltaTime); 

    const smoothRotate = (boneName, targetEuler) => {
        let bone = boneCache.get(boneName);
        if (bone === undefined) {
          bone = currentVrm.humanoid.getNormalizedBoneNode(boneName) || null;
          boneCache.set(boneName, bone);
        }
        if (bone) {
            bone.rotation.x = lerp(bone.rotation.x, targetEuler.x, smoothFactor);
            bone.rotation.y = lerp(bone.rotation.y, targetEuler.y, smoothFactor);
            bone.rotation.z = lerp(bone.rotation.z, targetEuler.z, smoothFactor);
        }
    };

    const smoothExpression = (expName, targetVal, factorOverride) => {
        const f = factorOverride ?? smoothFactor;
        const currentVal = currentVrm.expressionManager.getValue(expName);
        const newVal = lerp(currentVal, targetVal, f);
        currentVrm.expressionManager.setValue(expName, newVal);
    };

    const applyFingerCurl = (side, curlAmount) => {
        const fingerBones = ['Thumb', 'Index', 'Middle', 'Ring', 'Little'];
        const segments = ['Proximal', 'Intermediate', 'Distal'];
        
        fingerBones.forEach(finger => {
            segments.forEach(seg => {
                const boneName = `${side}${finger}${seg}`;
                const bone = currentVrm.humanoid.getNormalizedBoneNode(boneName);
                if (bone) {
                    let targetRot = curlAmount * 1.2;
                    if (finger === 'Thumb') {
                         targetRot = curlAmount * 0.65;
                         if (seg === 'Proximal') {
                             bone.rotation.y = lerp(bone.rotation.y, curlAmount * 0.5, smoothFactor);
                         }
                    }
                    bone.rotation.x = lerp(bone.rotation.x, -targetRot, smoothFactor);
                }
            });
        });
    };

    smoothRotate('hips', targets.hips);
    smoothRotate('neck', targets.neck);
    smoothRotate('head', targets.head);
    smoothRotate('chest', targets.chest);
    smoothRotate('spine', targets.spine);
    smoothRotate('leftShoulder', targets.leftShoulder);
    smoothRotate('rightShoulder', targets.rightShoulder);
    
    smoothRotate('leftEye', targets.leftEye);
    smoothRotate('rightEye', targets.rightEye);

    smoothRotate('leftUpperArm', targets.leftUpperArm);
    smoothRotate('leftLowerArm', targets.leftLowerArm);
    smoothRotate('leftHand', targets.leftHand);
    
    smoothRotate('rightUpperArm', targets.rightUpperArm);
    smoothRotate('rightLowerArm', targets.rightLowerArm);
    smoothRotate('rightHand', targets.rightHand);

    applyFingerCurl('left', targets.leftHandPose);
    applyFingerCurl('right', targets.rightHandPose);

    const blinkSmooth = 1.0 - Math.exp(-22.0 * deltaTime);
    smoothExpression('blink', targets.blink, blinkSmooth);
    smoothExpression('joy', targets.joy);
    smoothExpression('surprised', targets.surprised);
    smoothExpression('oh', targets.oh);
    smoothExpression('sorrow', targets.sorrow);
    smoothExpression('fun', targets.fun);
    
    if (isSpeaking) {
        currentVrm.expressionManager.setValue('aa', targets.aa);
        currentVrm.expressionManager.setValue('ih', targets.ih);
        currentVrm.expressionManager.setValue('ou', targets.ou);
        currentVrm.expressionManager.setValue('ee', targets.ee);
        currentVrm.expressionManager.setValue('oh', targets.oh_mouth);
    } else {
        smoothExpression('aa', targets.aa);
        smoothExpression('ih', 0);
        smoothExpression('ou', 0);
        smoothExpression('ee', 0);
        smoothExpression('oh', 0);
    }
  };

  onMount(() => {
    clock = new THREE.Clock();
    scene = new THREE.Scene();
    //scene.background = new THREE.Color(0x0f172a); 

    camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.1, 20.0);
    camera.position.set(0.0, 1.35, 1.1); 

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.423;

    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    canvasContainer.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0x2d3652, 1.5); 
    scene.add(ambientLight);

    const mainLight = new THREE.DirectionalLight(0xfff0dd, 2.0);
    mainLight.position.set(-1.5, 1.5, 1.0); 
    mainLight.castShadow = true; 
    mainLight.shadow.bias = -0.0001; 
    mainLight.shadow.mapSize.width = 1024;
    mainLight.shadow.mapSize.height = 1024;
    scene.add(mainLight);

    const rimLight = new THREE.DirectionalLight(0x5555ff, 1.0);
    rimLight.position.set(-1.0, 0.5, -1.0).normalize();
    scene.add(rimLight);
    
    scene.add(new THREE.AmbientLight(0x444444));

    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));

    loader.load(
      '/AlisaV2.vrm', 
      (gltf) => {
        const vrm = gltf.userData.vrm;
        VRMUtils.removeUnnecessaryVertices(gltf.scene);
        VRMUtils.rotateVRM0(vrm); 
        currentVrm = vrm;
        boneCache = new Map();
        scene.add(vrm.scene);
        vrm.scene.rotation.y = 0;
      },
      undefined,
      (error) => console.error(error)
    );

    function animate() {
      animationFrameId = requestAnimationFrame(animate);
      const deltaTime = clock.getDelta();

      if (currentVrm) {
        currentVrm.update(deltaTime);
        updateLogic(deltaTime);
        applySmoothMovement(deltaTime);
      }
      renderer.render(scene, camera);
    }
    animate();

    const handleMouseMove = (event) => {
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    };
    window.addEventListener('mousemove', handleMouseMove);

    const handleResize = () => {
      if (!canvasContainer) return;
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
        window.removeEventListener('resize', handleResize);
        window.removeEventListener('mousemove', handleMouseMove);
        cancelAnimationFrame(animationFrameId);
        renderer.dispose();
    };
  });
</script>

<div bind:this={canvasContainer} class="avatar-canvas"></div>

<style>
  .avatar-canvas { width: 100%; height: 100%; overflow: hidden; }
</style>