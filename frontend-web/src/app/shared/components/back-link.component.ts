import { Component, Input } from '@angular/core';
@Component({selector:'app-back-link',standalone:true,template:`<a class="back-link" [attr.href]="href">← {{label}}</a>`,styles:[`.back-link{display:inline-block;margin-bottom:1rem;color:#245b48;font-weight:700;text-decoration:none}.back-link:hover{text-decoration:underline}`]})
export class BackLinkComponent { @Input({required:true}) to!: string | any[]; @Input({required:true}) label!: string; get href():string{return Array.isArray(this.to)?this.to.join('/'):this.to;} }
