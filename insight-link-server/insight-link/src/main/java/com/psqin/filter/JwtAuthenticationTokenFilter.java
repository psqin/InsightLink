package com.psqin.filter;

import com.psqin.constant.JwtClaimsConstant;
import com.psqin.context.BaseContext;
import com.psqin.properties.JwtProperties;
import com.psqin.utils.JwtUtil;
import io.jsonwebtoken.Claims;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

@Component
@Slf4j
public class JwtAuthenticationTokenFilter extends OncePerRequestFilter {

    @Autowired
    private JwtProperties jwtProperties;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        String token = request.getHeader(jwtProperties.getAdminTokenName());

        if (StringUtils.hasText(token)) {
            try {
                log.info("Spring Security JWT filter checking token: {}", token);
                Claims claims = JwtUtil.parseJWT(jwtProperties.getAdminSecretKey(), token);
                Long userId = Long.valueOf(claims.get(JwtClaimsConstant.USER_ID).toString());
                Integer roleId = Integer.valueOf(claims.get(JwtClaimsConstant.ROLE_ID).toString());

                log.info("当前用户ID：{}, 角色ID：{}", userId, roleId);
                BaseContext.setCurrentId(userId);
                BaseContext.setRoleId(roleId);

                // Build authorities based on role
                List<GrantedAuthority> authorities = new ArrayList<>();
                authorities.add(new SimpleGrantedAuthority("ROLE_" + roleId));

                UsernamePasswordAuthenticationToken authenticationToken =
                        new UsernamePasswordAuthenticationToken(userId, null, authorities);
                authenticationToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

                SecurityContextHolder.getContext().setAuthentication(authenticationToken);

            } catch (Exception e) {
                log.error("Token verification failed: {}", e.getMessage());
                // Clear security context to force authentication exception
                SecurityContextHolder.clearContext();
                BaseContext.removeCurrentId();
                BaseContext.removeRoleId();
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                return;
            }
        }

        try {
            filterChain.doFilter(request, response);
        } finally {
            // Must clear BaseContext to avoid memory leak
            BaseContext.removeCurrentId();
            BaseContext.removeRoleId();
            SecurityContextHolder.clearContext();
        }
    }
}