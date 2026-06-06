package com.example.hellodemo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {

    @GetMapping("/api/hello")
    public HelloResponse hello() {
        return new HelloResponse("hello");
    }

    public record HelloResponse(String message) {
    }
}
