import { AfterViewInit, Component, ElementRef, Input, OnChanges, OnDestroy, SimpleChanges, ViewChild } from '@angular/core';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { AvatarParameterService, BodyProfile } from '../services/avatar-parameter.service';

@Component({
  selector: 'app-fitting-three-viewer',
  standalone: true,
  template: `<div class="viewer-shell" [class.is-fallback]="failed"><canvas #canvas aria-label="Avatar masculino 3D interactivo"></canvas><div class="viewer-badge"><span></span> VISTA 3D · 360°</div>@if (failed) {<p>Tu navegador no pudo inicializar la vista 3D.</p>}</div>`,
  styles: [`:host{display:block}.viewer-shell{position:relative;min-height:520px;overflow:hidden;border:1px solid #c8d4ce;border-radius:22px;background:radial-gradient(circle at 50% 18%,#f8fbf8,#dbe5df 52%,#b9c8bf);box-shadow:inset 0 0 80px #fff8}.viewer-shell canvas{display:block;width:100%;height:520px;cursor:grab}.viewer-shell canvas:active{cursor:grabbing}.viewer-badge{position:absolute;top:18px;left:18px;display:flex;gap:8px;align-items:center;padding:8px 11px;border:1px solid #ffffffaa;border-radius:999px;background:#17372dcc;color:#fff;font-size:10px;font-weight:700;letter-spacing:.12em}.viewer-badge span{width:7px;height:7px;border-radius:50%;background:#c6e8c4}.is-fallback{display:grid;place-items:center;color:#42534c}@media(max-width:640px){.viewer-shell,.viewer-shell canvas{min-height:400px;height:400px}}`]
})
export class FittingThreeViewerComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() garment: any | null = null;
  @Input() accessory = false;
  @Input() bodyProfile: BodyProfile | null = null;
  @ViewChild('canvas') canvas?: ElementRef<HTMLCanvasElement>;
  failed = false;
  private renderer?: THREE.WebGLRenderer;
  private scene?: THREE.Scene;
  private camera?: THREE.PerspectiveCamera;
  private controls?: OrbitControls;
  private frame = 0;
  private clothes?: THREE.Group;
  private accessoryGroup?: THREE.Group;

  ngAfterViewInit(): void { this.createScene(); }
  ngOnChanges(changes: SimpleChanges): void {
    if (this.scene && (changes['garment'] || changes['accessory'] || changes['bodyProfile'])) { this.applyBodyProfile(); this.updateLook(); }
  }

  private createScene(): void {
    const canvas = this.canvas?.nativeElement;
    if (!canvas) return;
    try {
      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.Fog(0xdbe5df, 7, 18);
      this.camera = new THREE.PerspectiveCamera(35, 1, .1, 100);
      this.camera.position.set(4.2, 2.8, 7.2);
      this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
      this.controls = new OrbitControls(this.camera, canvas);
      this.controls.target.set(0, 1.4, 0);
      this.controls.enableDamping = true;
      this.controls.minDistance = 4.2;
      this.controls.maxDistance = 10;
      this.controls.maxPolarAngle = Math.PI / 1.9;
      this.scene.add(new THREE.HemisphereLight(0xffffff, 0x315445, 2.2));
      const key = new THREE.DirectionalLight(0xfffbef, 3.2); key.position.set(4, 6, 5); this.scene.add(key);
      const rim = new THREE.DirectionalLight(0x89c6ac, 2); rim.position.set(-5, 3, -4); this.scene.add(rim);
      const floor = new THREE.Mesh(new THREE.CircleGeometry(3.2, 64), new THREE.MeshStandardMaterial({ color: 0xc4d1c8, roughness: .95 }));
      floor.rotation.x = -Math.PI / 2; floor.position.y = -.03; this.scene.add(floor);
      this.buildAvatar();
      this.updateLook();
      new ResizeObserver(() => this.resize()).observe(canvas);
      this.resize(); this.animate();
    } catch { this.failed = true; }
  }

  private buildAvatar(): void {
    if (!this.scene) return;
    const skin = new THREE.MeshStandardMaterial({ color: 0x9c725a, roughness: .75 });
    const body = new THREE.MeshStandardMaterial({ color: 0x26352f, roughness: .82 });
    const group = new THREE.Group(); group.name = 'avatar';
    const head = new THREE.Mesh(new THREE.SphereGeometry(.42, 32, 24), skin); head.position.y = 3.6; group.add(head);
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(.16, .17, .3, 18), skin); neck.position.y = 3.18; group.add(neck);
    const torso = new THREE.Mesh(new THREE.CapsuleGeometry(.7, 1.35, 10, 24), body); torso.scale.set(1.08, 1, .58); torso.position.y = 2.2; group.add(torso);
    for (const x of [-.88, .88]) { const arm = new THREE.Mesh(new THREE.CapsuleGeometry(.16, 1.2, 8, 16), skin); arm.position.set(x, 2.25, 0); arm.rotation.z = x * .12; group.add(arm); }
    for (const x of [-.3, .3]) { const leg = new THREE.Mesh(new THREE.CapsuleGeometry(.25, 1.65, 8, 16), body); leg.position.set(x, .75, 0); group.add(leg); }
    this.scene.add(group);
    this.applyBodyProfile();
  }

  private applyBodyProfile(): void { const avatar=this.scene?.getObjectByName('avatar'); if(!avatar)return; const p=AvatarParameterService.from(this.bodyProfile); avatar.scale.set(p.shoulderWidth,p.heightScale,p.torsoWidth); const torso=avatar.children[2]; if(torso)torso.scale.x=p.waistWidth; const legs=avatar.children.slice(-2); legs.forEach(leg=>leg.scale.y=p.legLength); }

  private updateLook(): void {
    if (!this.scene) return;
    this.clothes?.removeFromParent(); this.accessoryGroup?.removeFromParent();
    this.clothes = new THREE.Group();
    const name = `${this.garment?.nombre ?? ''}`.toLowerCase();
    const colorName = `${this.garment?.color ?? 'verde'}`.toLowerCase();
    const colors: Record<string, number> = { azul: 0x173e67, negro: 0x161718, blanco: 0xf4f2ea, gris: 0x586069, verde: 0x2c604e };
    const material = new THREE.MeshStandardMaterial({ color: colors[colorName] ?? 0x2c604e, roughness: .62, metalness: .03 });
    const isPants = name.includes('pantal') || this.garment?.garment === 'pants';
    if (isPants) {
      for (const x of [-.3, .3]) { const trouser = new THREE.Mesh(new THREE.CapsuleGeometry(.29, 1.62, 8, 16), material); trouser.position.set(x, .76, .01); this.clothes.add(trouser); }
      const waist = new THREE.Mesh(new THREE.BoxGeometry(1.18, .26, .55), material); waist.position.y = 1.6; this.clothes.add(waist);
    } else {
      const top = new THREE.Mesh(new THREE.CapsuleGeometry(.76, 1.36, 10, 24), material); top.scale.set(1.11, 1, .63); top.position.y = 2.22; this.clothes.add(top);
      for (const x of [-.9, .9]) { const sleeve = new THREE.Mesh(new THREE.CapsuleGeometry(.19, 1.08, 8, 16), material); sleeve.position.set(x, 2.27, .01); sleeve.rotation.z = x * .12; this.clothes.add(sleeve); }
      if (name.includes('chaqueta')) { const zipper = new THREE.Mesh(new THREE.BoxGeometry(.035, 1.25, .04), new THREE.MeshStandardMaterial({ color: 0xd5c5a3, metalness: .75 })); zipper.position.set(0, 2.22, .48); this.clothes.add(zipper); }
    }
    this.scene.add(this.clothes);
    if (this.accessory) { this.accessoryGroup = new THREE.Group(); const watch = new THREE.Mesh(new THREE.TorusGeometry(.13, .04, 12, 24), new THREE.MeshStandardMaterial({ color: 0xc6a765, metalness: .85, roughness: .25 })); watch.position.set(.95, 1.85, .02); watch.rotation.x = Math.PI / 2; this.accessoryGroup.add(watch); this.scene.add(this.accessoryGroup); }
  }

  private resize(): void { if (!this.renderer || !this.camera || !this.canvas) return; const { clientWidth: w, clientHeight: h } = this.canvas.nativeElement; this.renderer.setSize(w, h, false); this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); }
  private animate = (): void => { this.frame = requestAnimationFrame(this.animate); this.controls?.update(); this.renderer?.render(this.scene!, this.camera!); };
  ngOnDestroy(): void { cancelAnimationFrame(this.frame); this.controls?.dispose(); this.renderer?.dispose(); }
}
