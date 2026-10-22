package com.psqin.service.Impl;

import com.psqin.context.BaseContext;
import com.psqin.mapper.*;
import com.psqin.service.TeacherReportService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class TeacherReportServiceImpl implements TeacherReportService {

    @Autowired private TsGuidanceMapper tsGuidanceMapper;
    @Autowired private TsMessageMapper tsMessageMapper;
    @Autowired private NoticeMapper noticeMapper;
    @Autowired private StuMaterialMapper stuMaterialMapper;
    @Autowired private StuEvalMapper stuEvalMapper;

    @Override
    public Map<String, Object> overview() {
        Long teacherUserId = BaseContext.getCurrentId();

        Integer myStudents = tsGuidanceMapper.countByTeacherUserId(teacherUserId);

        LocalDate today = LocalDate.now();
        LocalDateTime beginTime = today.atStartOfDay();
        LocalDateTime endTime = today.plusDays(1).atStartOfDay();
        Integer todayStudentMessages = tsMessageMapper.countTodayStudentMessages(teacherUserId, beginTime, endTime);

        Integer myNotices = noticeMapper.countByTypeAndPublisher(2, teacherUserId);

        Integer evaluated = stuMaterialMapper.countEvaluatedByTeacherUserId(teacherUserId);
        Integer unevaluated = stuMaterialMapper.countUnevaluatedByTeacherUserId(teacherUserId);

        BigDecimal avgScore = stuEvalMapper.avgScoreByTeacherUserId(teacherUserId);
        BigDecimal avgScoreFixed = avgScore == null ? BigDecimal.ZERO : avgScore.setScale(2, RoundingMode.HALF_UP);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("myStudents", myStudents == null ? 0 : myStudents);
        data.put("todayStudentMessages", todayStudentMessages == null ? 0 : todayStudentMessages);
        data.put("myNotices", myNotices == null ? 0 : myNotices);
        data.put("unevaluated", unevaluated == null ? 0 : unevaluated);
        data.put("evaluated", evaluated == null ? 0 : evaluated);
        data.put("avgScore", avgScoreFixed);
        return data;
    }

    @Override
    public Map<String, Object> evalTrend(Integer days) {
        Long teacherUserId = BaseContext.getCurrentId();
        int d = days == null ? 30 : days;
        if (d < 1) d = 1;
        if (d > 90) d = 90;

        LocalDate end = LocalDate.now();
        LocalDate start = end.minusDays(d - 1);
        LocalDateTime startTime = start.atStartOfDay();

        List<String> labels = new ArrayList<>();
        for (LocalDate cur = start; !cur.isAfter(end); cur = cur.plusDays(1)) {
            labels.add(cur.toString());
        }

        List<com.psqin.domain.vo.DailyCountVO> records = stuEvalMapper.listDailyCountByTeacherUserId(teacherUserId, startTime);
        Map<String, Integer> map = records == null ? java.util.Collections.emptyMap() :
                records.stream().collect(Collectors.toMap(com.psqin.domain.vo.DailyCountVO::getDay, com.psqin.domain.vo.DailyCountVO::getCount));

        List<Integer> values = new ArrayList<>(labels.size());
        for (String day : labels) {
            values.add(map.getOrDefault(day, 0));
        }

        Map<String, Object> series = new LinkedHashMap<>();
        series.put("evalCount", values);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("labels", labels);
        data.put("series", series);
        return data;
    }
}
