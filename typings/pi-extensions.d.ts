declare module "@earendil-works/pi-ai" {
  export const StringEnum: any;
}
declare module "@earendil-works/pi-coding-agent" {
  export type ExtensionAPI = any;
  export function registerCommand(...args: any[]): any;
  export function on(event: string, cb: (...args: any[]) => any): any;
  export function exec(cmd: string, args?: any[], options?: any): Promise<any>;
  export function sendMessage(msg: any): void;
}
declare module "typebox" {
  export const Type: any;
  export function String(opts?: any): any;
  export const Number: any;
  export const Boolean: any;
}
