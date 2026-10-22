package com.psqin.config;

import com.psqin.filter.JwtAuthenticationTokenFilter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableGlobalMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;

@Configuration
@EnableWebSecurity
@EnableGlobalMethodSecurity(prePostEnabled = true)
public class SecurityConfig {

    @Autowired
    private JwtAuthenticationTokenFilter jwtAuthenticationTokenFilter;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                // Disable CSRF since we use token-based auth
                .csrf().disable()
                // Disable session management
                .sessionManagement().sessionCreationPolicy(SessionCreationPolicy.STATELESS)
                .and()
                // Authorize requests based on original interceptor rules
                .authorizeRequests()
                // Public endpoints
                .antMatchers("/user/login", "/user/register", "/user/forgetPassword", "/user/common/upload").permitAll()
                // Swagger/Knife4j endpoints
                .antMatchers("/doc.html", "/webjars/**", "/swagger-resources/**", "/v2/api-docs").permitAll()
                // WebSocket endpoints
                .antMatchers("/ws/**").permitAll()
                
                // Role-based path rules mimicking interceptor logic
                // roleId = 1 (Admin) can access everything (no explicit restriction needed if they have the token)
                // roleId = 2 (Teacher) cannot access /student/**
                // roleId = 3 (Student) cannot access /teacher/**
                
                // If it's a student path, Role 1 or Role 3 can access. Role 2 cannot.
                .antMatchers("/student/**").hasAnyRole("1", "3")
                // If it's a teacher path, Role 1 or Role 2 can access. Role 3 cannot.
                .antMatchers("/teacher/**").hasAnyRole("1", "2")
                // Only Admin can access admin path
                .antMatchers("/admin/**").hasRole("1")
                
                // All other requests must be authenticated
                .anyRequest().authenticated();

        // Add our custom JWT filter before the standard UsernamePasswordAuthenticationFilter
        http.addFilterBefore(jwtAuthenticationTokenFilter, UsernamePasswordAuthenticationFilter.class);

        // Allow CORS if needed
        http.cors();

        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(Arrays.asList("*"));
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"));
        configuration.setAllowedHeaders(Arrays.asList("*"));
        configuration.setAllowCredentials(false);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
}