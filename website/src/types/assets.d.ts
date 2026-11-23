// Webpack resolves these to a hashed URL; Docusaurus ships no typings for them.
declare module "*.webp" {
  const src: string;
  export default src;
}
declare module "*.png" {
  const src: string;
  export default src;
}
