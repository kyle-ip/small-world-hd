#ifdef GL_ES
precision mediump float;
#endif

uniform sampler2D s_texture;
uniform vec2 u_texSizeInv;
uniform float u_kernelRadius;

varying vec2 v_texCoord;

void main()
{
#ifdef GL_ES
 #if __VERSION__ < 300
 #define CONSTANT_FOR_LOOP_CONDITION 1
 #endif
#endif


#ifdef CONSTANT_FOR_LOOP_CONDITION
    int radius = 7;
#else
    int radius = int(max(1.0, floor(u_kernelRadius * 0.72)));
#endif

    vec2 loc = v_texCoord;
    float alpha = texture2D(s_texture, loc).a;
    for (int i=1; i<= radius; i++) {
        float u = u_texSizeInv.x*float(i);
        for (int j=1; j<=radius; j++) {
            float v = u_texSizeInv.y*float(j);
            alpha = max(alpha, texture2D(s_texture, loc + vec2(  u,   v)).a);
            alpha = max(alpha, texture2D(s_texture, loc + vec2(- u,   v)).a);
            alpha = max(alpha, texture2D(s_texture, loc + vec2(  u, - v)).a);
            alpha = max(alpha, texture2D(s_texture, loc + vec2(- u, - v)).a);
        }
    }

    gl_FragColor = vec4(1.0, 1.0, 1.0, alpha);
}