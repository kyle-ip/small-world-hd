#ifdef GL_ES
precision mediump float;
#endif

uniform sampler2D s_texture;
uniform vec2 u_direction;
uniform int u_max_pixel_delta;
uniform float u_pd_inv_2x_sigma2;
uniform float u_pd_norm;

varying vec2 v_texCoord;

// https://en.wikipedia.org/wiki/Normal_distribution

void main()
{
    float coefAccumulation = u_pd_norm;
    vec4 colorAccumulation = texture2D(s_texture, v_texCoord) * coefAccumulation;
    
    for (int i = 1; i <= u_max_pixel_delta; i++) {
        float coeff = u_pd_norm * exp(- float(i) * float(i) * u_pd_inv_2x_sigma2);
        
        vec2 delta = float(i) * u_direction * 0.72;
        
        // Left
        vec2 leftCoord = v_texCoord - delta;
        if (0.0 <= leftCoord.x && leftCoord.x <= 1.0 && 0.0 <= leftCoord.y && leftCoord.y <= 1.0)
        {
            coefAccumulation += coeff;
            colorAccumulation += texture2D(s_texture, leftCoord) * coeff;
        }
            
        // Right
        vec2 rightCoord = v_texCoord + delta;
        if (0.0 <= rightCoord.x && rightCoord.x <= 1.0 && 0.0 <= rightCoord.y && rightCoord.y <= 1.0)
        {
            coefAccumulation += coeff;
            colorAccumulation += texture2D(s_texture, rightCoord) * coeff;
        }
    }
    
    gl_FragColor = colorAccumulation / coefAccumulation;
}
